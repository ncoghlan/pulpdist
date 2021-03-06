#
# Copyright (C) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""sync_trees - utilities for synchronising trees with rsync"""

from datetime import datetime
import logging
import os
from os import path
import sys # We use stdout for testing purposes
import shellutil
import shutil
import subprocess
import traceback
import collections
import re
import contextlib
import errno

from . import sync_config, util

_BASE_FETCH_DIR_PARAMS = """
    -rlptDvH --delete-after --ignore-errors --progress --stats --human-readable
    --timeout=18000 --partial --delay-updates
""".split()

# Rsync statistics collection
_sync_stats_pattern = re.compile(r"""
Number of files: (?P<total_file_count>\d+)
Number of files transferred: (?P<transferred_file_count>\d+)
Total file size: (?P<total_size>[.\d]+)(?P<total_size_kind>[BKMG]?) bytes
Total transferred file size: (?P<transferred_size>[.\d]+)(?P<transferred_size_kind>[BKMG]?) bytes
Literal data: (?P<literal_size>[.\d]+)(?P<literal_size_kind>[BKMG]?) bytes
Matched data: (?P<matched_size>[.\d]+)(?P<matched_size_kind>[BKMG]?) bytes
File list size: (?P<listing_size>[.\d]+)(?P<listing_size_kind>[BKMG]?)
File list generation time: (?P<listing_creation_seconds>[.\d]+) seconds
File list transfer time: (?P<listing_transfer_seconds>[.\d]+) seconds
Total bytes sent: (?P<sent_size>[.\d]+)(?P<sent_size_kind>[BKMG]?)
Total bytes received: (?P<received_size>[.\d]+)(?P<received_size_kind>[BKMG]?)

sent [.\d]+[BKMG]? bytes\s+received [.\d]+[BKMG]? bytes\s+(?P<transfer_rate>[.\d]+)(?P<transfer_rate_kind>[BKMG]?)\s+bytes/sec
""", re.DOTALL)

_old_sync_stats_pattern = re.compile(r"""
Number of files: (?P<total_file_count>\d+)
Number of files transferred: (?P<transferred_file_count>\d+)
Total file size: (?P<total_size>[.\d]+)(?P<total_size_kind>[BKMG]?) bytes
Total transferred file size: (?P<transferred_size>[.\d]+)(?P<transferred_size_kind>[BKMG]?) bytes
Literal data: (?P<literal_size>[.\d]+)(?P<literal_size_kind>[BKMG]?) bytes
Matched data: (?P<matched_size>[.\d]+)(?P<matched_size_kind>[BKMG]?) bytes
File list size: (?P<listing_size>[.\d]+)(?P<listing_size_kind>[BKMG]?)
Total bytes sent: (?P<sent_size>[.\d]+)(?P<sent_size_kind>[BKMG]?)
Total bytes received: (?P<received_size>[.\d]+)(?P<received_size_kind>[BKMG]?)

sent [.\d]+[BKMG]? bytes\s+received [.\d]+[BKMG]? bytes\s+(?P<transfer_rate>[.\d]+)(?P<transfer_rate_kind>[BKMG]?)\s+bytes/sec
""", re.DOTALL)


_kind_scale = {
    None : 1,
    ''   : 1,
    'B'  : 1,
    'K'  : 1024,
    'M'  : 1024*1024,
    'G'  : 1024*1024*1024,
    'T'  : 1024*1024*1024*1024,
}

def _bytes_from_size_and_kind(size, kind):
    scale = _kind_scale[kind]
    return int(float(size) * scale)

_sync_stats_fields = """
  total_file_count transferred_file_count
  total_bytes transferred_bytes
  literal_bytes matched_bytes
  sent_bytes received_bytes
  transfer_bps
  listing_bytes listing_creation_seconds listing_transfer_seconds
""".split()

class SyncStats(collections.namedtuple("SyncStats", _sync_stats_fields)):
    def __add__(self, other):
        if not isinstance(other, SyncStats):
            return NotImplemented
        return SyncStats(*(a + b for a, b in zip(self, other)))

    @classmethod
    def from_rsync_output(cls, raw_data, old_daemon=False):
        stats = collections.defaultdict(int)
        scraped = None
        if old_daemon:
            pattern = _old_sync_stats_pattern
        else:
            pattern = _sync_stats_pattern
        for scraped in pattern.finditer(raw_data):
            data = scraped.groupdict()
            if old_daemon:
                data["listing_creation_seconds"] = 0
                data["listing_transfer_seconds"] = 0
            for field in SyncStats._fields:
                if field.endswith("_count"):
                    stats[field] += int(data[field])
                elif field.endswith("_seconds"):
                    stats[field] += float(data[field])
                elif field.endswith("_bps"):
                    field_prefix = field.rpartition('_')[0]
                    rate = data[field_prefix + "_rate"]
                    kind = data[field_prefix + "_rate_kind"]
                    stats[field] += _bytes_from_size_and_kind(rate, kind)
                else:
                    field_prefix = field.rpartition('_')[0]
                    size = data[field_prefix + "_size"]
                    kind = data[field_prefix + "_size_kind"]
                    stats[field] += _bytes_from_size_and_kind(size, kind)
        if scraped is None:
            raise ValueError("No rsync stats found in output")
        return cls(**stats)

_null_sync_stats = SyncStats(*([0]*len(SyncStats._fields)))

# rsync remote ls scraping

_remote_ls_entry_pattern = re.compile(
"^(?P<entry_kind>.).*"
" (?P<mtime>\d\d\d\d\/\d\d\/\d\d \d\d:\d\d:\d\d)"
" (?P<entry_details>.*)$", re.MULTILINE)


class BaseSyncCommand(object):

    SYNC_UP_TO_DATE = "SYNC_UP_TO_DATE"
    SYNC_COMPLETED = "SYNC_COMPLETED"
    SYNC_PARTIAL = "SYNC_PARTIAL"
    SYNC_FAILED = "SYNC_FAILED"
    SYNC_DISABLED = "SYNC_DISABLED"

    DRY_RUN_SUFFIX = "_DRY_RUN"

    CONFIG_TYPE = None

    def __init__(self, config, log_dest=None):
        config_type = self.CONFIG_TYPE
        if config_type is None:
            raise NotImplementedError("CONFIG_TYPE not set by subclass")
        config_data = config_type(config)
        config_data.validate()
        self.__dict__.update(config_data.config)
        self._init_run_log(log_dest)

    def _init_run_log(self, log_dest):
        self._run_log_indent_level = 0
        if log_dest is None:
            self._run_log_file = None
        elif isinstance(log_dest, basestring):
            # Use line buffered output by default
            self._run_log_file = open(log_dest, 'w', 1)
        else:
            self._run_log_file = log_dest
        self._update_run_log("Log initialised: {0} {1}",
                             type(self).__name__,
                             util.__version__)

    @contextlib.contextmanager
    def _indent_run_log(self, level=None):
        old_level = self._run_log_indent_level
        if level is None:
            level = old_level + 1
        self._run_log_indent_level = level
        try:
            yield
        finally:
            self._run_log_indent_level = old_level

    def _update_run_log(self, _fmt, *args, **kwds):
        if self._run_log_file is None:
            return
        fmt = ("  " * self._run_log_indent_level) + _fmt
        if args:
            msg = fmt.format(*args, **kwds)
        else:
            msg = fmt
        self._run_log_file.write(msg.rstrip() + '\n')

    @contextlib.contextmanager
    def _flush_run_log(self):
        if self._run_log_file is None:
            yield
        else:
            try:
                yield
            finally:
                self._run_log_file.flush()

    def _run_shell_command(self, cmd):
        shell_output = []
        with self._indent_run_log(0):
            self._update_run_log("_"*75)
            self._update_run_log("Getting shell output for:\n\n  {0}\n\n", cmd)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
            for line in proc.stdout:
                shell_output.append(line)
                self._update_run_log(line)
            result = proc.wait()
            self._update_run_log("^"*75)
        return result, "".join(shell_output)

    def _consolidate_tree(self):
        local_path = self.local_path
        hardlink_cmd = ["hardlink", "-v", self.local_path]
        try:
            return_code, __ = self._run_shell_command(hardlink_cmd)
        except:
            self._update_run_log(traceback.format_exc())
            result_msg = "Exception while hard linking duplicates in {0!r}"
        else:
            if return_code == 0:
                result_msg = "Successfully hard linked duplicates in {0!r}"
            else:
                result_msg = "Failed to hard link duplicates in {0!r}"
        self._update_run_log(result_msg, local_path)


    def _send_amqp_message(self, result, sync_stats):
        details = "{0!r} transfer {1!r} -> {2!r}: {3}, {4}".format(
            self.tree_name, self.remote_path, self.local_path, result, sync_stats)
        if self.dry_run_only:
            msg = "Not sending AMQP message for test run ({0})"
        msg = "AMQP support not yet implemented ({0})"
        self._update_run_log(msg, details)

    def _run_sync_inner(self):
        start_time = datetime.utcnow()
        if not self.enabled:
            self._update_run_log("Ignoring sync request for {0!r} at {1}", self.tree_name, start_time)
            return self.SYNC_DISABLED, start_time, start_time, _null_sync_stats

        self._update_run_log("Syncing tree {0!r} at {1}", self.tree_name, start_time)

        with self._indent_run_log():
            if self.dry_run_only:
                self._update_run_log("Performing test run (no file transfer)")
            elif not path.exists(self.local_path):
                self._update_run_log("Local path {0!r} does not exist, creating it", self.local_path)
                try:
                    os.makedirs(self.local_path, 0755)
                except OSError as ex:
                    if ex.errno != errno.EEXIST:
                        raise
                    self._update_run_log("  Destination directory already created by another process")

            result, sync_stats = self._do_transfer()

            if sync_stats.transferred_file_count > 0:
                self._update_run_log("Consolidating downloaded data with hard links")
                with self._indent_run_log():
                    self._consolidate_tree()
                self._update_run_log("Sending AMQP message")
                with self._indent_run_log():
                    self._send_amqp_message(result, sync_stats)

        finish_time = datetime.utcnow()
        if self.dry_run_only:
            result += self.DRY_RUN_SUFFIX

        msg = "Completed sync of {0!r} at {1} (Result: {2}, Duration: {3})"
        self._update_run_log(msg, self.tree_name,
                             finish_time, result, finish_time - start_time)
        return result, start_time, finish_time, sync_stats

    def run_sync(self):
        """Execute the full synchronisation task

           Ensures the sync log is flushed before returing
        """
        with self._flush_run_log():
            return self._run_sync_inner()


    def _build_common_rsync_params(self):
        """Construct rsync parameters common to all operations"""
        params = []
        if self.old_remote_daemon:
            params.append("--no-implied-dirs")
        if self.rsync_port:
            params.append("--port={0}".format(self.rsync_port))
        return params

    def _build_fetch_dir_rsync_params(self, remote_source_path, local_dest_path,
                                      local_seed_paths=()):
        """Construct rsync parameters to fetch a remote directory"""
        params = _BASE_FETCH_DIR_PARAMS[:]
        params.extend(self._build_common_rsync_params())
        if self.dry_run_only:
            params.append("-n")
        if self.bandwidth_limit:
            params.append("--bwlimit={0}".format(self.bandwidth_limit))
        # Add sync filters
        for rsync_filter in self.sync_filters:
            params.append("--filter={0}".format(rsync_filter))
        # Add exclude filters
        for excluded_file in self.exclude_from_sync:
            params.append("--exclude={0}".format(excluded_file))
        # Protect directories from deletion if they contain a file called PROTECTED
        for dir_info in shellutil.filtered_walk(local_dest_path, file_pattern='PROTECTED'):
            if dir_info.files:
                rel_path = dir_info.path
                if os.path.isabs(rel_path):
                    rel_path = os.path.relpath(rel_path, local_dest_path)
                params.append("--filter=protect {0}".format(rel_path))
        for seed_path in local_seed_paths:
            params.append("--link-dest={0}".format(seed_path))
        params.append(remote_source_path)
        params.append(local_dest_path)
        return params

    def _scrape_fetch_dir_rsync_stats(self, data):
        try:
            return SyncStats.from_rsync_output(data, self.old_remote_daemon)
        except ValueError:
            self._update_run_log("No stats data found in rsync output")
            raise RuntimeError("No stats data found in rsync output")

    def _fetch_dir_complete(self, result, remote_source_path, local_dest_path):
        return result

    def fetch_dir(self, remote_source_path, local_dest_path, local_seed_paths=()):
        """Fetch a single directory from the remote server"""
        params = self._build_fetch_dir_rsync_params(remote_source_path,
                                                    local_dest_path,
                                                    local_seed_paths)
        rsync_fetch_command = ["rsync"] + params
        rsync_stats = _null_sync_stats
        self._update_run_log("Downloading {0!r} -> {1!r}", remote_source_path, local_dest_path)
        for seed_path in local_seed_paths:
            self._update_run_log("Using {0!r} as local seed data", seed_path)
        if not self.dry_run_only:
            # Remove any previously synchronised files and symlinks that have
            # have been changed to directories on the source server
            if (os.path.lexists(local_dest_path) and
                (os.path.islink(local_dest_path) or
                 not os.path.isdir(local_dest_path))):
                self._update_run_log("Unlinking {0!r} (replacing with directory)", local_dest_path)
                os.unlink(local_dest_path)
            # Ensure the full path to the destination directory exists locally
            if not os.path.lexists(local_dest_path):
                self._update_run_log("Creating destination directory {0!r}", local_dest_path)
                try:
                    os.makedirs(local_dest_path)
                except OSError as ex:
                    if ex.errno != errno.EEXIST:
                        raise
                    self._update_run_log("  Destination directory already created by another process")
        with self._indent_run_log():
            try:
                return_code, captured = self._run_shell_command(rsync_fetch_command)
            except:
                self._update_run_log(traceback.format_exc())
                result_msg = "Exception while updating {0!r} from {1!r}"
            else:
                if return_code in (0, 23):
                    with self._indent_run_log():
                        rsync_stats = self._scrape_fetch_dir_rsync_stats(captured)
                        self._update_run_log("Retrieved rsync stats:")
                        with self._indent_run_log():
                            for field, value in zip(rsync_stats._fields, rsync_stats):
                                self._update_run_log("{0}={1}", field, value)
                    if return_code == 23:
                        result_msg = "Partially updated {0!r} from {1!r}"
                        result = self.SYNC_PARTIAL
                    elif rsync_stats.transferred_file_count == 0:
                        result_msg = "{0!r} already up to date relative to {1!r} (or all updates were found in seed directory)"
                        result = self.SYNC_UP_TO_DATE
                    else:
                        result_msg = "Successfully updated {0!r} from {1!r}"
                        result = self.SYNC_COMPLETED
                    # We give subclasses a chance to second guess the nominal result
                    # as well as taking other actions
                    result = self._fetch_dir_complete(result, remote_source_path, local_dest_path)
                else:
                    result_msg = "Non-zero return code (%d) updating {0!r} from {1!r}" % return_code
                    result = self.SYNC_FAILED
            self._update_run_log(result_msg, local_dest_path, remote_source_path)
        return result, rsync_stats


class SyncTree(BaseSyncCommand):
    """Sync the contents of a directory"""
    CONFIG_TYPE = sync_config.TreeSyncConfig

    def _do_transfer(self):
        remote_source_path = "rsync://{0}{1}".format(self.remote_server, self.remote_path)
        local_dest_path = self.local_path
        return self.fetch_dir(remote_source_path, local_dest_path)


class SyncVersionedTree(BaseSyncCommand):
    """Sync the contents of a directory containing multiple versions of a tree"""
    CONFIG_TYPE = sync_config.VersionedSyncConfig

    def _build_remote_ls_rsync_params(self, remote_ls_path):
        """Construct rsync parameters to get a remote directory listing"""
        params = ["-nl"]
        if self.old_remote_daemon:
            # The common params handles adding --no-implied-dirs, but the
            # directory listing operation also needs this option
            params.append("--old-d")
        params.extend(self._build_common_rsync_params())
        # Filter out unwanted directories
        for subdir_filter in self.listing_filters:
            params.append("--filter={0}".format(subdir_filter))
        for excluded_pattern in self.exclude_from_listing:
            params.append("--exclude={0}".format(excluded_pattern))
        params.append(remote_ls_path)
        return params

    def _scrape_rsync_remote_ls(self, data):
        dir_entries = []
        link_entries = []
        for entry in re.finditer(_remote_ls_entry_pattern, data):
            kind = entry.group("entry_kind")
            details = entry.group("entry_details")
            if kind == 'l':
                link_entries.append(details.strip())
            elif kind == 'd':
                mtime = entry.group("mtime")
                dir_entries.append((mtime, details.strip()))
            else:
                self._update_run_log("Unknown entry kind {0!r}", entry)
        self._update_run_log("Identified directories {0!r}", dir_entries)
        self._update_run_log("Identified symlinks {0!r}", link_entries)
        return dir_entries, link_entries

    def remote_ls(self, remote_ls_path):
        params = self._build_remote_ls_rsync_params(remote_ls_path)
        rsync_ls_command = ["rsync"] + params
        self._update_run_log("Getting remote listing for {0!r}", remote_ls_path)
        dir_entries = link_entries = ()
        with self._indent_run_log():
            try:
                return_code, captured = self._run_shell_command(rsync_ls_command)
            except:
                self._update_run_log(traceback.format_exc())
                result_msg = "Exception while listing {0!r}"
            else:
                if return_code == 0:
                    result_msg = "Successfully listed {0!r}"
                    with self._indent_run_log():
                        dir_entries, link_entries = self._scrape_rsync_remote_ls(captured)
                else:
                    result_msg = "Non-zero return code ({0:d}) listing {{0!r}}".format(return_code)
            self._update_run_log(result_msg, remote_ls_path)
        return dir_entries, link_entries

    def _iter_local_versions(self):
        local_path = self.local_path
        dir_info = shellutil.filtered_walk(local_path,
                                           dir_pattern=self.listing_pattern,
                                           excluded_dirs=self.exclude_from_listing,
                                           depth=0).next()
        for d in dir_info.subdirs:
            yield os.path.join(local_path, d)

    def _get_initial_seed_paths(self):
        # By default, there are no initial seed paths
        return ()

    def _iter_remote_versions(self, remote_dir_entries):
        seed_paths = self._get_initial_seed_paths()
        for mtime, version in sorted(remote_dir_entries):
            remote_version = self.remote_path + version
            remote_source_path = "rsync://{0}{1}/".format(self.remote_server, remote_version)
            local_dest_path = os.path.join(self.local_path, version)
            yield remote_source_path, local_dest_path, seed_paths
            # If it exists, use the previous tree as the seed for the next one
            if os.path.isdir(local_dest_path):
                seed_paths = (local_dest_path,)

    def _already_retrieved(self, local_dest_path):
        # Local directories are overwritten by default
        return False

    def _should_retrieve(self, remote_source_path):
        # Remote directories are retrieved by default
        return True

    def _fix_link_entries(self, remote_link_entries):
        # ensure local symlinks match remote ones
        self._update_run_log("Ensuring local validity of upstream symlinks")
        with self._indent_run_log():
            local_path = self.local_path
            for ls_entry in remote_link_entries:
                link_path, target_path = re.search("([^ ]*) -> ([^ ]*)$", ls_entry).groups()
                # If those paths are absolute, os.path.join will just ignore 'local_path'
                link_path = os.path.join(local_path, link_path)
                full_target_path = os.path.join(local_path, target_path)
                self._update_run_log("Checking symlink '{0} -> {1}'", link_path, target_path)
                # Only care about symlinks to directories that exist on the local system
                if not os.path.exists(full_target_path):
                    self._update_run_log("Local {0!r} does not exist, ignoring symlink {1!r}", full_target_path, ls_entry)
                    continue
                if not os.path.isdir(full_target_path):
                    self._update_run_log("Local {0!r} is not a directory, ignoring symlink {1!r}", full_target_path, ls_entry)
                    continue
                if os.path.islink(full_target_path):
                    old_target_link = os.path.join(os.path.dirname(full_target_path), os.readlink(full_target_path))
                    if os.path.samefile(old_target_link, link_path):
                        self._update_run_log("Local {0!r} links back to {1!r}, ignoring symlink {2!r}", full_target_path, link_path, ls_entry)
                        continue
                if os.path.lexists(link_path):
                    if os.path.islink(link_path):
                        old_link_target = os.readlink(link_path)
                        if old_link_target == target_path:
                            self._update_run_log("Symlink {0!r} already exists at {1!r}", ls_entry, link_path)
                            continue
                        self._update_run_log("Unlinking old symlink '{0} -> {1}'", link_path, old_link_target)
                        os.unlink(link_path)
                    elif os.path.isdir(link_path):
                        if os.path.exists(os.path.join(link_path, "PROTECTED")):
                            self._update_run_log("Skipping existing directory {0!r} (PROTECTED file found)", link_path)
                            continue
                        self._update_run_log("Removing old directory {0!r}", link_path)
                        shutil.rmtree(link_path)
                    else:
                        self._update_run_log("Unlinking old file {0!r}", link_path)
                        os.unlink(link_path)
                self._update_run_log("Creating symlink '{0} -> {1}'", link_path, target_path)
                os.symlink(target_path, link_path)

    def _delete_old_dirs(self, remote_dir_entries):
        self._update_run_log("Checking for removal of directories on remote server")
        dirs_to_delete = self._get_old_dirs(remote_dir_entries)
        return self._delete_local_dirs(dirs_to_delete)

    def _get_old_dirs(self, remote_dir_entries):
        local_dirs = set(os.path.basename(d) for d in self._iter_local_versions())
        remote_dirs = set(d for mtime, d in remote_dir_entries)
        return sorted(local_dirs - remote_dirs)

    def _delete_local_dirs(self, dirs_to_delete):
        local_path = self.local_path
        deleted = 0
        with self._indent_run_log():
            for dirname in dirs_to_delete:
                dirpath = os.path.join(local_path, dirname)
                if os.path.exists(os.path.join(dirpath, "PROTECTED")):
                    self._update_run_log("Not deleting {0!r} (PROTECTED file found)", dirpath)
                    continue
                self._update_run_log("Deleting {0!r} (not on remote server)", dirpath)
                shutil.rmtree(dirpath)
                deleted += 1
        return deleted

    def _do_transfer(self):
        sync_stats = _null_sync_stats
        remote_pattern = os.path.join(self.remote_path, self.listing_pattern)
        remote_ls_path = "rsync://{0}{1}".format(self.remote_server, remote_pattern)
        dir_entries, link_entries = self.remote_ls(remote_ls_path)
        if not dir_entries:
            self._update_run_log("No relevant directories found at {0!r}", remote_ls_path)
            return self.SYNC_FAILED, sync_stats
        tallies = collections.defaultdict(int)
        for remote_source_path, local_dest_path, local_seed_paths in self._iter_remote_versions(dir_entries):
            self._update_run_log("Preparing to download {0!r} -> {1!r}", remote_source_path, local_dest_path)
            if self._already_retrieved(local_dest_path):
                self._update_run_log("Skipping download for {0!r} -> {1!r} (already completed)", remote_source_path, local_dest_path)
                continue
            if not self._should_retrieve(remote_source_path):
                self._update_run_log("Skipping download for {0!r} -> {1!r} (source not ready)", remote_source_path, local_dest_path)
                continue
            dir_result, dir_stats = self.fetch_dir(remote_source_path, local_dest_path, local_seed_paths)
            tallies[dir_result] += 1
            sync_stats += dir_stats
        if link_entries:
            self._fix_link_entries(link_entries)
        up_to_date = tallies[self.SYNC_UP_TO_DATE]
        completed = tallies[self.SYNC_COMPLETED]
        partial = tallies[self.SYNC_PARTIAL]
        failed = tallies[self.SYNC_FAILED]
        deleted = 0
        if self.delete_old_dirs:
            if failed or partial:
                self._update_run_log("Errors occurred, not deleting old directories in {0!r}", self.local_path)
            else:
                deleted = self._delete_old_dirs(dir_entries)
        if failed and not (partial or completed or up_to_date):
            # Absolutely nothing worked
            result = self.SYNC_FAILED
        elif failed or partial:
            # Got at least some failures
            result = self.SYNC_PARTIAL
        elif completed or deleted:
            # Had to actually do something
            result = self.SYNC_COMPLETED
        else:
            # Everything was already up to date
            result = self.SYNC_UP_TO_DATE
        return result, sync_stats

class SyncSnapshotTree(SyncVersionedTree):
    """Sync the contents of a directory containing multiple snapshots of a tree"""
    CONFIG_TYPE = sync_config.SnapshotSyncConfig

    def _find_latest_remote_version(self, remote_dir_entries):
        seed_paths = self._get_initial_seed_paths()
        for mtime, dir_entry in sorted(remote_dir_entries, reverse=True):
            remote_entry = self.remote_path + dir_entry
            remote_source_path = "rsync://{0}{1}/".format(self.remote_server, remote_entry)
            local_dest_path = os.path.join(self.local_path, dir_entry)
            yield remote_source_path, local_dest_path, seed_paths
            # Keep going until we successfully copy a tree to the local system
            if self._already_retrieved(local_dest_path):
                self._update_run_log("Latest remote tree is in {0!r}", local_dest_path)
                break
        else:
            self._update_run_log("No valid remote tree identified")

    def _iter_remote_versions(self, remote_dir_entries):
        if self.sync_latest_only:
            return self._find_latest_remote_version(remote_dir_entries)
        return super(SyncSnapshotTree, self)._iter_remote_versions(remote_dir_entries)

    def _already_retrieved(self, local_dest_path):
        local_status_path = os.path.join(local_dest_path, "STATUS")
        with self._indent_run_log():
            self._update_run_log("Checking for STATUS file in {0!r}", local_dest_path)
            with self._indent_run_log():
                if os.path.exists(local_status_path):
                    with open(local_status_path) as f:
                        status = f.read().strip()
                        self._update_run_log("Current status of {0!r} is {1!r}", local_dest_path, status)
                        return status == "FINISHED"
                else:
                    self._update_run_log("No STATUS file found in {0!r}", local_dest_path)
        return False

    def _should_retrieve(self, remote_source_path):
        with shellutil.temp_dir() as tmpdir:
          with self._indent_run_log():
            tmp_local_status = os.path.join(tmpdir, "STATUS")
            remote_status_path = os.path.join(remote_source_path, "STATUS")
            params = self._build_common_rsync_params()
            params.append(remote_status_path)
            params.append(tmp_local_status)
            self._update_run_log("Checking for STATUS file in {0!r}", remote_source_path)
            with self._indent_run_log():
                rsync_status_command = ["rsync"] + params
                try:
                    return_code, __ = self._run_shell_command(rsync_status_command)
                except:
                    self._update_run_log(traceback.format_exc())
                    result_msg = "Exception while attempting to check status of {0!r}"
                else:
                    if os.path.exists(tmp_local_status):
                        with open(tmp_local_status) as f:
                            status = f.read().strip()
                            self._update_run_log("Current status of {0!r} is {1!r}", remote_source_path, status)
                            return status == "FINISHED"
                    else:
                        result_msg = "No STATUS file found in {0!r}"
                self._update_run_log(result_msg, remote_source_path)
        return False

    def _fetch_dir_complete(self, result, remote_source_path, local_dest_path):
        if result == self.SYNC_PARTIAL:
            return result
        status_path = os.path.join(local_dest_path, "STATUS")
        if result == self.SYNC_UP_TO_DATE and os.path.exists(status_path):
            # Tree actually *was* up to date, we didn't just get lucky
            # and manage to hard link everything
            return result
        result = self.SYNC_COMPLETED
        if not self.dry_run_only:
            with open(status_path, 'w') as f:
                f.write("FINISHED\n")
            self._link_to_latest(local_dest_path)
        return result

    def _get_latest_dir(self):
        # Preferred approach is to use the symbolic link to the latest version
        link_name = self.latest_link_name
        if link_name is not None:
            link_path = os.path.join(self.local_path, link_name)
            if os.path.isdir(link_path):
                target_path = os.path.join(link_path, os.readlink(link_path))
                return os.path.abspath(target_path)
        # If that's not available, we rely on the local mtime
        def _sort_key(d):
            return os.path.getmtime(d), d
        candidates = self._iter_local_versions()
        try:
            return max(candidates, key=_sort_key)
        except ValueError:
            pass
        return None

    def _get_initial_seed_paths(self):
        # Use the most recent local dir as the initial seed path
        latest_dir = self._get_latest_dir()
        return (latest_dir,) if latest_dir is not None else ()

    def _get_old_dirs(self, remote_dir_entries):
        dirs_to_delete = (super(SyncSnapshotTree, self).
                                _get_old_dirs(remote_dir_entries))
        # Never delete latest entry, even if it's gone from the remote server
        latest_dir = self._get_latest_dir()
        if latest_dir is not None:
            dirname = os.path.basename(latest_dir)
            try:
                dirs_to_delete.remove(dirname)
            except ValueError:
                pass
        return dirs_to_delete

    def _link_to_latest(self, target_path):
        link_name = self.latest_link_name
        if link_name is None:
            return
        local_path = self.local_path
        link_path = os.path.join(local_path, link_name)
        self._update_run_log("Updating {0!r} symlink to refer to latest version", link_path)
        with self._indent_run_log():
            if self.dry_run_only:
                self._update_run_log("Skipping creation of {0!r} for test run", link_path)
                return
            if target_path is None:
                self._update_run_log("No valid target versions in {0!r}, skipping", local_path)
                return
            relative_target = os.path.relpath(target_path, os.path.dirname(link_path))
            if os.path.isdir(link_path):
                if os.path.islink(link_path):
                    if os.readlink(link_path) == relative_target:
                        self._update_run_log("Link {0!r} -> {1!r} already exists", link_path, relative_target)
                        return
                    os.unlink(link_path)
                else:
                    self._update_run_log("Existing latest directory, {0!r}, is not a symbolic link, deleting it", link_path)
                    shutil.rmtree(link_path)
            elif os.path.lexists(link_path):
                self._update_run_log("Existing entry, {0!r}, is not a directory, deleting it", link_path)
                os.unlink(link_path)
            os.symlink(relative_target, link_path)
            self._update_run_log("Linked {0!r} -> {1!r}", link_path, relative_target)


class SyncSnapshotDelta(BaseSyncCommand):
    """Create an rsync delta from a snapshot directory"""

    def __init__(self):
        raise NotImplemented("Depends on Pulp plugin details")

class SyncFromDelta(BaseSyncCommand):
    """Create a new local snapshots from an upstream delta"""
    def __init__(self):
        raise NotImplemented("Depends on Pulp plugin details")
