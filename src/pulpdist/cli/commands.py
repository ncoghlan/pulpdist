#!/usr/bin/env python
"""Request synchronisation of repos based on a JSON config"""
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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.\

import argparse
import json
import socket
import webbrowser
import tempfile
import os.path
import contextlib
import datetime

from ..core.pulpapi import PulpServerClient, ServerRequestError
from ..core.repo_config import RepoConfig
from ..core.site_config import SiteConfig, PulpRepo
from .display import (print_msg, print_header, print_data,
                      print_repo_table, catch_server_error)
from .thread_pool import ThreadPool, PendingTasks

# TODO: The whole structure of the metadata updating and management is
#       very clumsy. Need to tidy it up and make it easy to apply deltas
#       that will then be correctly reflected in a subsequent export.
#       BZ#801251 (requesting a separate 'add' command) is relevant

#====================================================
# Meta-description of the supported "args" attributes
#====================================================

def default_host():
    """Returns a meaningful default hostname.

       Tries socket.getfqdn() first, but falls back to socket.gethostname()
       if getfqdn() returns "localhost.localdomain" (as it does on a default
       Fedora install)
    """
    fqdn = socket.getfqdn()
    if fqdn != "localhost.localdomain":
        return fqdn
    return socket.gethostname()


def make_args(pulp_host=None, verbose=0, ignoremeta=False,
              config_fname=None, num_entries=None, current_hour=None,
              showlog=False, dryrun=False, success=False, force=False,
              num_threads=4,
              repo_list=(), mirror_list=(), site_list=(),
              tree_list=(), source_list=(), server_list=()):
    """Creates a valid "args" attribute suitable for passing to any
       command initialiser. Not all parameters make sense for all commands.

       See repo_cli.py for the parameter descriptions and applicability to
       the various commands.
    """
    if pulp_host is None:
        pulp_host = default_host()
    args = argparse.Namespace()
    vars(args).update(locals())
    del args.args
    return args


#================================================================
# Basic commands - work directly off the site metadata
#================================================================

class PulpCommand(object):
    """Operations on PulpDist managed Pulp repositories"""

    def __init__(self, args, server=None):
        self.args = args
        self._site_config = None
        if server is None:
            server = PulpServerClient(args.pulp_host)
        self.server = server

    @property
    def site_config(self):
        if self._site_config is not None:
            return self._site_config
        self._load_site_config()
        return self._site_config

    def _load_site_config(self, upload_meta=False):
        """Read site config from file or server. Return value indicates if we
        read a new site config from file or not.
        """
        args = self.args
        verbose = args.verbose
        config_fname = args.config_fname
        if config_fname is None:
            upload_meta = False
            server = self.server
            if verbose:
                print_msg("Loading configuration from host {0!r}", server.host)
            config_data = None
            if not args.ignoremeta:
                with catch_server_error() as ex:
                    config_data = server.get_site_config()
            if config_data is None:
                config_data = server.get_repos()
                if verbose:
                    print_msg("Handling all repos on server as raw trees")
                for tree in config_data:
                    tree["repo_id"] = tree.pop("id")
                config_data = {"RAW_TREES": config_data}
        else:
            if verbose:
                print_msg("Loading configuration from file {0!r}", config_fname)
            with open(config_fname) as config_file:
                config_data = json.load(config_file)
        self._site_config = site_config = SiteConfig(config_data)
        if verbose > 2:
            print_data(site_config.config, 2)
        if upload_meta:
            self.upload_metadata(site_config)

    def upload_metadata(self):
        raise NotImplementedError

    def _get_repos(self):
        """Returns a list of (repo_id, display_id, repo_info) tuples

        The display_id is just a more nicely formatted alternative to the
        combined repo_id used for local mirror definitions. For raw trees, it
        is the same as repo_id.
        """
        args = self.args
        repo_configs = self.site_config.get_repo_configs(
            repos = args.repo_list,
            mirrors = args.mirror_list,
            trees = args.tree_list,
            sources = args.source_list,
            servers = args.server_list,
            sites = args.site_list
        )
        if not repo_configs:
            return []
        repos = [PulpRepo.from_config(r) for r in repo_configs]
        repos.sort()
        return repos

    def __call__(self):
        repos = self._get_repos()
        self.process_repos(repos)

    def print_no_repos(self):
        """Report the case of an empty repo list to the user"""
        print_msg("No relevant repositories identified")

    def process_repos(self, repos):
        """Process the repo list"""
        if not repos:
            if self.args.verbose:
                self.print_no_repos()
            return
        for repo in repos:
            self.process_repo(repo)

    def process_repo(self, repo):
        """Process an individual repo"""
        raise NotImplementedError


class ValidateRepoConfig(PulpCommand):
    """Command that simply checks the site metadata validity"""
    def process_repo(self, repo):
        print_msg("Config for {0} is valid", repo.display_id)


class ShowRepoSummary(PulpCommand):
    """Command that simply lists basic repo information"""
    def process_repos(self, repos):
        """Process the repo list"""
        if not repos:
            self.print_no_repos()
            return
        print_msg("Repositories defined on {0!r}:", self.server.host)
        print_repo_table("{display_name}", repos)


class ShowRepoDetails(PulpCommand):
    """Command that displays the full repo configuration"""
    def process_repo(self, repo):
        display_id = repo.display_id
        print_msg("Repository details for {0}", display_id)
        with catch_server_error("Failed to retrieve {0}", display_id):
            data = self.server.get_repo(repo.id)
            print_data(data)


#================================================================
# History commands - also require sync history details
#================================================================

class SyncHistoryCommand(PulpCommand):
    """Operations on Pulp repositories that require sync history details"""

    def _get_repos(self):
        """Returns a list of (repo_id, display_id, repo_info) tuples

        The repo_info includes sync history details in addition to the repo
        config data provided by PulpCommand.

        The display_id is just a more nicely formatted alternative to the
        combined repo_id used for local mirror definitions. For raw trees, it
        is the same as repo_id.
        """
        server = self.server
        repos = super(SyncHistoryCommand, self)._get_repos()
        for repo in repos:
            details = repo.config
            history_error = "Failed to retrieve sync history for {0}"
            details["sync_history"] = None
            details["last_attempt"] = None
            details["last_success"] = None
            with catch_server_error(history_error, repo.display_id):
                details["sync_history"] = history = server.get_sync_history(repo.id)
                if not history:
                    continue
                details["last_attempt"] = history[0]
                for sync in history:
                    summary = sync["summary"]
                    if summary is None:
                        continue
                    result = summary["result"]
                    if result in "SYNC_COMPLETED SYNC_UP_TO_DATE".split():
                        details["last_success"] = sync
                        break
        return repos


class ShowRepoStatus(SyncHistoryCommand):
    """Command that displays the sync status of each repository"""

    def process_repos(self, repos):
        field_format = "{0:30}{1:30}{2}"
        headings = field_format.format("Last Sync", "Last Attempt", "Last Result")
        for repo_id, display_id, repo in repos:
            history = repo["sync_history"]
            if history is None:
                repo["sync_summary"] = "Failed to retrieve sync history"
                continue
            last_attempt = repo["last_attempt"]
            if last_attempt is None:
                repo["sync_summary"] = "Never synchronised"
                continue
            attempt_summary = last_attempt["summary"]
            if attempt_summary is None:
                attempt_result = "PLUGIN_ERROR"
            else:
                attempt_result = attempt_summary["result"]
            attempt_time = last_attempt["started"]
            last_success = repo["last_success"]
            if last_success is None:
                success_time = "Never"
            else:
                success_time = last_success["started"]
            repo["sync_summary"] = field_format.format(success_time, attempt_time, attempt_result)
        print_msg("Sync status for repositories on {0!r}", self.server.host)
        print_repo_table("{sync_summary}", repos, headings)


class ShowSyncHistory(SyncHistoryCommand):
    """Command that displays the sync history of each repository"""
    def process_repo(self, repo):
        history = repo.config["sync_history"]
        if not history:
            print_msg("No sync history for {0}", repo.display_id)
            return
        args = self.args
        num_entries = args.num_entries
        if num_entries is not None:
            history = history[:num_entries]
        print_header("Sync history for {0}", repo.display_id)
        for sync_job in history:
            details = sync_job.get("details")
            if details and not args.showlog:
                details.pop("sync_log", None)
            print_data(sync_job)

class LatestSyncCommand(SyncHistoryCommand):
    """Operations that need to access the latest success or attempt"""
    def get_latest_sync(self, repo):
        display_success = self.args.success
        sync_version = "last_success" if display_success else "last_attempt"
        sync_job = repo.config[sync_version]
        if sync_job is None:
            if display_success:
                err_msg = "No successful sync entry for {0}"
            else:
                err_msg = "No sync attempts for {0}"
            print_msg(err_msg, repo.display_id)
        return sync_job


class ShowSyncLog(LatestSyncCommand):
    """Command that displays the most recent sync log of each repository"""
    def process_repo(self, repo):
        sync_job = self.get_latest_sync(repo)
        if sync_job is None:
            return
        # See BZ#799203 for more info on why this works this way
        host = self.args.pulp_host
        print_header("Most recent sync log for {0}", repo.display_id)
        log_url = "https://{0}/sync_logs/{1}.log".format(host, repo.id)
        print_msg("Opening '{0}' in browser".format(log_url))
        webbrowser.open_new_tab(log_url)


class ShowSyncStats(LatestSyncCommand):
    """Command that displays the most recent sync stats for each repository"""
    def process_repo(self, repo):
        display_id = repo.display_id
        sync_job = self.get_latest_sync(repo)
        if sync_job is None:
            return
        summary = sync_job["summary"]
        if summary is None:
            print("No sync details for {0}".format(display_id))
            return
        print_header("Most recent sync statistics for {0}", display_id)
        print_data(summary["stats"])


#================================================================
# Modification commands - actually modify server state
#================================================================

class ModificationCommand(PulpCommand):
    """Operations on Pulp repositories that modify the repo configuration"""
    # Messages are passed a single positional parameter for the repo id
    # Don't include the " (y/n):" in the prompt, that's added automatically
    FMT_PROMPT = None
    FMT_SKIP = None
    FMT_ATTEMPT = None
    FMT_FAILED = None
    FMT_SUCCESS = None

    def _confirm_operation(self, display_id):
        """Prompt for confirmation of action (assume OK if --force used)"""
        if self.args.force:
            return True
        prompt = self.FMT_PROMPT.format(display_id)
        response = raw_input(prompt + " (y/n):")
        return response.lower() in ('y', 'yes')

    def process_repo(self, repo):
        def _fmt(name):
            return "  " + getattr(self, "FMT_" + name)

        verbose = self.args.verbose
        display_id = repo.display_id
        if not self._confirm_operation(display_id):
            if verbose:
                print_msg(_fmt("SKIP"), display_id)
            return
        if verbose:
            print_msg(_fmt("ATTEMPT"), display_id)
        with catch_server_error(_fmt("FAILED"), display_id) as ex:
            self.modify_repo(repo)
        if not ex:
            print_msg(_fmt("SUCCESS"), display_id)
        # TODO: Also modify site metadata
        # self.upload_meta()

    def modify_repo(self, repo):
        raise NotImplementedError


class RequestSync(ModificationCommand):
    FMT_PROMPT = "Synchronise {0}?"
    FMT_SKIP = "Not synchronising {0}"
    FMT_ATTEMPT = "Synchronising {0}"
    FMT_FAILED = "Failed to synchronise {0}"
    FMT_SUCCESS = "Synchronised {0}"

    def modify_repo(self, repo):
        self.server.sync_repo(repo.id)
        # TODO: Also modify site metadata

class EnableSync(ModificationCommand):
    FMT_PROMPT = "Enable sync for {0}?"
    FMT_SKIP = "Not enabling sync on {0}"
    FMT_ATTEMPT = "Enabling sync on {0}"
    FMT_FAILED = "Failed to enable sync on {0}"
    FMT_SUCCESS = "Enabled sync on {0}"

    def modify_repo(self, repo):
        self.server.enable_sync(repo.id, self.args.dryrun)
        # TODO: Also modify site metadata

class DisableSync(ModificationCommand):
    FMT_PROMPT = "Disable sync for {0}?"
    FMT_SKIP = "Not disabling sync on {0}"
    FMT_ATTEMPT = "Disabling sync on {0}"
    FMT_FAILED = "Failed to disable sync on {0}"
    FMT_SUCCESS = "Disabled sync on {0}"

    def modify_repo(self, repo):
        self.server.disable_sync(repo.id)
        # TODO: Also modify site metadata

class DeleteRepo(ModificationCommand):
    FMT_PROMPT = "Delete {0}?"
    FMT_SKIP = "Not deleting {0}"
    FMT_ATTEMPT = "Deleting {0}"
    FMT_FAILED = "Failed to delete {0}"
    FMT_SUCCESS = "Deleted {0}"

    def modify_repo(self, repo):
        self.server.delete_repo(repo.id)
        # TODO: Also modify site metadata

#================================================================
# Special commands - commands that don't fit the standard pattern
#================================================================

class InitialiseRepos(ModificationCommand):
    FMT_PROMPT = "Initialise {0}"

    def upload_metadata(self, site_config):
        if not self._confirm_operation("PulpDist site metadata"):
            raise RuntimeError("Cannot configure from site definition without "
                               "updating site metadata first")
        if self.args.verbose:
            print_msg("Initialising site metadata")
        err_msg = "Failed to save PulpDist site config metadata to server"
        with catch_server_error(err_msg) as ex:
            self.server.save_site_config(site_config.config)
        if ex: # Failed to save metadata, abort
            raise ex[0]

    def _load_site_config(self):
        # Unlike other commands, this one can change the server's metadata
        super(InitialiseRepos, self)._load_site_config(upload_meta=True)

    def process_repos(self, repos):
        args = self.args
        verbose = args.verbose
        server = self.server
        for repo_id, display_id, repo in self._get_repos():
            if not self._confirm_operation(display_id):
                if verbose:
                    print_msg("Not initialising {0}", display_id)
                continue
            if verbose:
                print_msg("Creating or updating {0}", display_id)
            if verbose > 1:
                print_msg("Configuration:")
                print_data(repo)
            with catch_server_error("Failed to create or update {0}", display_id) as ex:
                server.create_or_save_repo(
                    repo_id,
                    repo.get("display_name", None),
                    repo.get("description", None),
                    repo.get("notes", None))
            if ex:
                continue
            if verbose:
                print_msg("Created or updated {0}", display_id)
            importer_id = repo.get("importer_type_id", None)
            if importer_id is not None:
                if verbose:
                    print_msg("Adding {0} importer to {1}", importer_id, display_id)
                err_msg = "Failed to add {0} importer to {1}"
                with catch_server_error(err_msg, importer_id, display_id):
                    server.add_importer(repo_id,
                                        importer_id,
                                        repo.get("importer_config", None))
                if verbose:
                    print_msg("Added {0} importer to {1}", importer_id, display_id)
            if verbose > 1:
                print_msg("Checking repository details for {0}", display_id)
                with catch_server_error("Failed to retrieve {0}", display_id):
                    data = server.get_repo(repo_id)
                    print_data(data)

class ScheduledSync(PulpCommand):
    _LOCK_DIR = os.path.join(tempfile.gettempdir(), "pulpdist_cron_sync.lock")

    def get_current_hour(self):
        current_hour = self.args.current_hour
        if current_hour is not None:
            return current_hour
        return datetime.datetime.now().hour

    def queue_for_sync(self, pool, priority, repo):
        print_msg("{0} is scheduled for synchronisation", repo.display_id)
        if pool is None:
            return
        pool.add_task(priority, self.server.sync_repo, repo.id)

    def get_sync_hours(self, repo):
        try:
            return repo[u"notes"][u"pulpdist"][u"sync_hours"]
        except KeyError:
            pass
        return None

    def _make_thread_pool(self):
        if self.args.dryrun:
            return None
        return ThreadPool(self.args.num_threads)


    def sync_loop(self):
        # Some details of note:
        #   - jobs that are checked more often are treated as higher priority
        #     when multiple jobs are picked up in a single pass through the
        #     repo list. This is the reason jobs are not enqueued immediately
        #     when found in the list.
        #   - the "already enqueued" set includes the current hour value in
        #     case sync operations take a long time and the command is still
        #     running when a previously synchronised repo comes up for
        #     synchronisation again
        #   - this command is designed to be run once per hour. Running it more
        #     often may result in the same sync job being executed multiple
        #     times during the relevant hours. Unscheduled sync jobs should be
        #     requested directly via the "sync" command
        verbose = self.args.verbose
        server = self.server
        enqueued = set()
        pool = self._make_thread_pool()
        poll_frequency = 300 # Check for new jobs every 5 minutes
        while 1:
          current_hour = self.get_current_hour()
          if verbose:
              print_msg("Current hour is {0}", current_hour)
          all_repos = self._get_repos()
          jobs_to_enqueue = []
          for repo in all_repos:
              if (repo.display_id, current_hour) in enqueued:
                  continue
              sync_hours = self.get_sync_hours(repo.config)
              if not sync_hours: # 0 and None both mean "no scheduled sync"
                  continue
              if current_hour % sync_hours != 0:
                  continue
              if server.sync_enabled(repo.id):
                  jobs_to_enqueue.append((sync_hours, repo))
          jobs_to_enqueue.sort()
          for sync_hours, repo in jobs_to_enqueue:
              self.queue_for_sync(pool, sync_hours, repo)
              enqueued.add((repo.display_id, current_hour))
          if pool is not None:
              try:
                  pool.wait_for_tasks(poll_frequency)
              except PendingTasks:
                  # Some tasks are still running, so just go around again to
                  # see if any new tasks need to be scheduled
                  continue
          if enqueued:
              print_msg("No further repos require synchronisation")
          else:
              print_msg("No repos require synchronisation")
          break

    @contextlib.contextmanager
    def _cron_sync_lock(self):
        try:
            os.mkdir(self._LOCK_DIR)
        except OSError:
            print_msg("Failed to create lock dir {0}", self._LOCK_DIR)
            yield False
        else:
            try:
                yield True
            finally:
                os.rmdir(self._LOCK_DIR)

    def __call__(self):
        with self._cron_sync_lock() as acquired_lock:
            if acquired_lock:
                self.sync_loop()

def _export_repos(args):
    raise NotImplementedError
