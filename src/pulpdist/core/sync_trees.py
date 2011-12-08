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
import subprocess
import traceback
import collections
import re
import tempfile
import contextlib

from . import sync_config

_OLD_DAEMON = True

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
.+sent.+bytes\s+(?P<transfer_rate>[\d.]+)(?P<transfer_rate_kind>[BKMG]?)\s+bytes/sec
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

_null_sync_stats = SyncStats(*([0]*len(SyncStats._fields)))

# rsync remote ls scraping

_remote_ls_entry_pattern = re.compile(
"^(?P<entry_kind>.).*"
" (?P<mtime>\d\d\d\d\/\d\d\/\d\d \d\d:\d\d:\d\d)"
" (?P<entry_details>[^\s]*)$", re.MULTILINE)


class BaseSyncCommand(object):

    SYNC_UP_TO_DATE = "SYNC_UP_TO_DATE"
    SYNC_COMPLETED = "SYNC_COMPLETED"
    SYNC_PARTIAL = "SYNC_PARTIAL"
    SYNC_FAILED = "SYNC_FAILED"

    CONFIG_TYPE = None

    def __init__(self, config):
        config_type = self.CONFIG_TYPE
        if config_type is None:
            raise NotImplementedError("CONFIG_TYPE not set by subclass")
        config_data = config_type(config)
        config_data.validate()
        self.__dict__.update(config_data.config)

    def _init_run_log(self):
        self._run_log_indent_level = 0
        if self.log_path is None:
            self._run_log_file = sys.stdout
        else:
            self._run_log_file = open(self.log_path, 'w')

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
        fmt = ("  " * self._run_log_indent_level) + _fmt
        if args:
            msg = fmt.format(*args, **kwds)
        else:
            msg = fmt
        self._run_log_file.write(msg.rstrip() + '\n')
        self._run_log_file.flush()

    def _log_shell_output(self, cmd):
        shell_output = []
        with self._indent_run_log(0):
            self._update_run_log("_"*75)
            self._update_run_log("Getting shell output for:\n\n  {0}\n", cmd)
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                                     stderr=subprocess.STDOUT)
            for line in proc.stdout:
                shell_output.append(line)
                self._update_run_log(line)
            result = proc.wait()
            self._update_run_log("^"*75)
        return result, "".join(shell_output)

    def _consolidate_tree(self):
        local_path = self.local_path
        hardlink_cmd = "hardlink -v " + self.local_path
        try:
            return_code, __ = self._log_shell_output(hardlink_cmd)
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
        if self.is_test_run:
            msg = "Not sending AMQP message for test run ({0})"
        msg = "AMQP support not yet implemented ({0})"
        self._update_run_log(msg, details)

    def run_sync(self):
        """Execute the full synchronisation task"""
        self._init_run_log()
        start_time = datetime.utcnow()
        self._update_run_log("Syncing tree {0!r} at {1}", self.tree_name, start_time)

        with self._indent_run_log():
            if self.is_test_run:
                self._update_run_log("Performing test run (no file transfer)")
            elif not path.exists(self.local_path):
                self._update_run_log("Local path {0!r} does not exist, creating it", self.local_path)
                os.makedirs(self.local_path, 0755)

            result, sync_stats = self._do_transfer()

            if sync_stats.transferred_file_count > 0:
                self._update_run_log("Consolidating downloaded data with hard links")
                with self._indent_run_log():
                    self._consolidate_tree()
                self._update_run_log("Sending AMQP message")
                with self._indent_run_log():
                    self._send_amqp_message(result, sync_stats)

        finish_time = datetime.utcnow()
        msg = "Completed sync of {0!r} at {1} (Result: {2}, Duration: {3})"
        self._update_run_log(msg, self.tree_name,
                             finish_time, result, finish_time - start_time)
        return result, start_time, finish_time, sync_stats

    def _build_common_rsync_params(self):
        """Construct rsync parameters common to all operations"""
        params = []
        if self.old_remote_daemon:
            params.append("--old-d")
        if self.rsync_port:
            params.append("--port={0}".format(self.rsync_port))
        return params
        
    def _build_fetch_dir_rsync_params(self, remote_source_path, local_dest_path,
                                      local_seed_paths=()):
        """Construct rsync parameters to fetch a remote directory"""
        params = _BASE_FETCH_DIR_PARAMS[:]
        params.extend(self._build_common_rsync_params())
        if self.is_test_run:
            params.append("-n")
        if self.bandwidth_limit:
            params.append("--bwlimit={0}".format(self.bandwidth_limit))
        # Add sync filters
        for rsync_filter in self.sync_filters:
            params.append("--filter={0}".format(rsync_filter))
        # Add exclude filters
        for excluded_file in self.excluded_files:
            params.append("--exclude={0}".format(excluded_file))
        # Protect directories from deletion if they contain a file called PROTECTED
        for dir_info in shellutil.filtered_walk(local_dest_path, file_pattern='PROTECTED'):
            if dir_info.files:
                rel_path = dir_info.path
                if os.path.isabs(rel_path):
                    rel_path = os.path.relpath(rel_path, local_dest_path)
                params.append("--filter='protect {0}'".format(rel_path))
        for seed_path in local_seed_paths:
            params.append("--link-dest={0}".format(seed_path))
        params.append(remote_source_path)
        params.append(local_dest_path)
        return params

    def _scrape_fetch_dir_rsync_stats(self, data):
        scraped = _sync_stats_pattern.search(data)
        if scraped is None:
            self._update_run_log("No stats data found in rsync output")
            raise RuntimeError("No stats data found in rsync output")
        data = scraped.groupdict()
        stats = {}
        for field in SyncStats._fields:
            if field.endswith("_count"):
                stats[field] = int(data[field])
            elif field.endswith("_seconds"):
                stats[field] = float(data[field])
            elif field.endswith("_bps"):
                field_prefix = field.rpartition('_')[0]
                rate = data[field_prefix + "_rate"]
                kind = data[field_prefix + "_rate_kind"]
                stats[field] = _bytes_from_size_and_kind(rate, kind)
            else:
                field_prefix = field.rpartition('_')[0]
                size = data[field_prefix + "_size"]
                kind = data[field_prefix + "_size_kind"]
                stats[field] = _bytes_from_size_and_kind(size, kind)
        return SyncStats(**stats)

    def _fetch_dir_complete(self, result, remote_source_path, local_dest_path):
        return result

    def fetch_dir(self, remote_source_path, local_dest_path, local_seed_paths=()):
        """Fetch a single directory from the remote server"""
        params = self._build_fetch_dir_rsync_params(remote_source_path,
                                                    local_dest_path,
                                                    local_seed_paths)
        rsync_fetch_command = "rsync " + " ".join(params)
        rsync_stats = _null_sync_stats
        self._update_run_log("Downloading {0!r} -> {1!r}", remote_source_path, local_dest_path)
        for seed_path in local_seed_paths:
            self._update_run_log("Using {0!r} as local seed data", seed_path)
        if not self.is_test_run and not os.path.exists(local_dest_path):
            self._update_run_log("Creating destination directory {0!r}", local_dest_path)
            os.makedirs(local_dest_path)
        with self._indent_run_log():
            try:
                return_code, captured = self._log_shell_output(rsync_fetch_command)
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
                        result_msg = "{1!r} already up to date relative to {0!r}"
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
        params.extend(self._build_common_rsync_params())
        # Filter out unwanted directories
        for subdir_filter in self.subdir_filters:
            params.append("--filter={0}".format(subdir_filter))
        for excluded_version in self.excluded_versions:
            params.append("--exclude={0}".format(excluded_version))
        params.append(remote_ls_path)
        return params

    def _scrape_rsync_remote_ls(self, data):
        dir_entries = []
        link_entries = []
        for entry in re.finditer(_remote_ls_entry_pattern, data):
            kind = entry.group("entry_kind")
            details = entry.group("entry_details")
            if kind == 'l':
                link_entries.append(details)
            elif kind == 'd':
                mtime = entry.group("mtime")
                dir_entries.append((mtime, details))
        return dir_entries, link_entries

    def remote_ls(self, remote_ls_path):
        params = self._build_remote_ls_rsync_params(remote_ls_path)
        rsync_ls_command = "rsync " + " ".join(params)
        self._update_run_log("Getting remote listing for {0!r}", remote_ls_path)
        dir_entries = link_entries = ()
        with self._indent_run_log():
            try:
                return_code, captured = self._log_shell_output(rsync_ls_command)
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
                                           dir_pattern=self.version_pattern,
                                           excluded_dirs=self.excluded_versions,
                                           depth=0).next()
        for d in dir_info.subdirs:
            yield os.path.join(local_path, d)

    def _iter_remote_versions(self, remote_dir_entries):
        seed_paths = ()
        for mtime, version in sorted(remote_dir_entries):
            remote_version = self.remote_path + version
            remote_source_path = "rsync://{0}{1}/".format(self.remote_server, remote_version)
            local_dest_path = os.path.join(self.local_path, version)
            yield remote_source_path, local_dest_path, seed_paths
            # Use the previous tree as the seed for the next one
            seed_paths = (local_dest_path,)

    def _already_retrieved(self, local_dest_path):
        # Local directories are overwritten by default
        return False

    def _should_retrieve(self, remote_source_path):
        # Remote directories are retrieved by default
        return True

    def _fix_link_entries(self, remote_link_entries):
        pass

    def _delete_old_dirs(self, remote_dir_entries):
        pass

    def _do_transfer(self):
        sync_stats = _null_sync_stats
        remote_pattern = os.path.join(self.remote_path, self.version_pattern)
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
        self._fix_link_entries(link_entries)
        self._delete_old_dirs(dir_entries)
        up_to_date = tallies[self.SYNC_UP_TO_DATE]
        completed = tallies[self.SYNC_COMPLETED]
        partial = tallies[self.SYNC_PARTIAL]
        failed = tallies[self.SYNC_FAILED]
        if failed and not (partial or completed or up_to_date):
            # Absolutely nothing worked
            result = self.SYNC_FAILED
        elif failed or partial:
            # Got at least some failures
            result = self.SYNC_PARTIAL
        elif completed:
            # Had to actually do something
            result = self.SYNC_COMPLETED
        else:
            # Everything was already up to date
            result = self.SYNC_UP_TO_DATE
        return result, sync_stats

class SyncSnapshotTree(SyncVersionedTree):
    """Sync the contents of a directory containing multiple snapshots of a tree"""
    CONFIG_TYPE = sync_config.SnapshotSyncConfig

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
                rsync_status_command = "rsync " + " ".join(params)
                try:
                    return_code, __ = self._log_shell_output(rsync_status_command)
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
        with open(status_path, 'w') as f:
            f.write("FINISHED\n")
        return result

    def _link_to_latest(self):
        link_name = self.latest_link_name
        if link_name is None:
            return
        local_path = self.local_path
        link_path = os.path.join(local_path, link_name)
        self._update_run_log("Updating {0!r} symlink to refer to latest version", link_path)
        with self._indent_run_log():
            if self.is_test_run:
                self._update_run_log("Skipping creation of {0!r} for test run", link_path)
                return
            try:
                target_path = max(self._iter_local_versions(), key=os.path.getmtime)
            except ValueError:
                self._update_run_log("No valid target versions in {0!r}, skipping", local_path)
                return
            if os.path.isdir(link_path) and not os.path.islink(link_path):
                self._update_run_log("Existing latest directory, {0}, is not a symbolic link, deleting it", link_path)
                shutil.rmtree(link_path)
            relative_target = os.path.relpath(target_path, os.path.dirname(link_path))
            os.symlink(relative_target, link_path)
            self._update_run_log("Linked {0!r} -> {1!r}", link_path, relative_target)

    def _do_transfer(self):
        result, sync_stats = super(SyncSnapshotTree, self)._do_transfer()
        self._link_to_latest()
        return result, sync_stats



class SyncSnapshotDelta(BaseSyncCommand):
    """Create an rsync delta from a snapshot directory"""

    def __init__(self):
        raise NotImplemented("Depends on Pulp plugin details")

class SyncFromDelta(BaseSyncCommand):
    """Create a new local snapshots from an upstream delta"""
    def __init__(self):
        raise NotImplemented("Depends on Pulp plugin details")
