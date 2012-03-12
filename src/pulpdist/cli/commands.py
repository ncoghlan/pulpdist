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

from ..core.pulpapi import PulpServerClient, ServerRequestError
from ..core.repo_config import RepoConfig
from ..core.site_config import SiteConfig, PulpRepo
from .display import (print_msg, print_header, print_data,
                      print_repo_table, catch_server_error)

# TODO: The whole structure of the metadata updating and management is
#       clumsy and broken. Need to tidy it up and make it easy to apply
#       deltas that will then be correctly reflected in a subsequent export.

#================================================================
# Basic commands - work directly off the site metadata
#================================================================

class PulpCommand(object):
    """Operations on PulpDist managed Pulp repositories"""

    def __init__(self, args):
        self.args = args
        self._site_config = None
        self.server = PulpServerClient(args.pulp_host)

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
            server = self.server
            if verbose:
                print_msg("Loading configuration from host {0!r}", server.host)
            config_data = None
            if not args.ignoremeta:
                with catch_server_error() as ex:
                    config_data = server.get_site_config()
            if config_data is None:
                config_data = server.get_repos()
        else:
            if verbose:
                print_msg("Loading configuration from file {0!r}", config_fname)
            with open(config_fname) as config_file:
                config_data = json.load(config_file)
        if isinstance(config_data, list):
            upload_meta = False
            if verbose:
                print_msg("Converting raw config format to site config format")
            for tree in config_data:
                tree["repo_id"] = tree.pop("id")
            config_data = {"RAW_TREES": config_data}
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
        num_entries = args.num_entries
        if num_entries is not None:
            history = history[:num_entries]
        for sync_job in history:
            details = sync_job.get("details")
            if details and not args.showlog:
                details.pop("sync_log", None)
            print_msg(format_data(sync_job))

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
        display_id = repo.display_id
        sync_job = self.get_latest_sync(repo)
        details = sync_job["details"]
        if details is None:
            print_msg("No sync details for {0}", display_id)
            return
        print_header("Most recent sync log for {0}", display_id)
        print_msg(details["sync_log"])


class ShowSyncStats(LatestSyncCommand):
    """Command that displays the most recent sync stats for each repository"""
    def process_repo(self, repo):
        display_id = repo.display_id
        sync_job = self.get_latest_sync(repo)
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
    FMT_PROMPT = "{0}"

    def upload_metadata(self):
        if not self._confirm_operation("Initialise PulpDist site metadata"):
            raise RuntimeError("Cannot configure from site definition without "
                               "updating site metadata first")
        if verbose:
            print_msg("Initialising site metadata")
        err_msg = "Failed to save PulpDist site config metadata to server"
        with catch_server_error(err_msg) as ex:
            server.save_site_config(self.site_config.config)
        if ex: # Failed to save metadata, abort
            sys.exit(-1)

    def _load_metadata(self):
        # Unlike other commands, this on can change the server's metadata
        super(InitialiseRepos, self)._load_metadata(upload_meta=True)

    def process_repos(self, repos):
        verbose = args.verbose
        server = self.server
        for repo_id, display_id, repo in _get_repos(args):
            if not _confirm_operation("Initialise", display_id, args):
                if verbose:
                    print("Not initialising {0}".format(display_id))
                continue
            if verbose:
                print("Creating or updating {0}".format(display_id))
            if verbose > 1:
                print("Configuration:")
                print(_format_data(repo))
            try:
                server.create_or_save_repo(
                    repo_id,
                    repo.get("display_name", None),
                    repo.get("description", None),
                    repo.get("notes", None))
            except ServerRequestError, ex:
                msg = "Failed to create or update {0}".format(display_id)
                _print_server_error(msg, ex)
                continue
            if verbose:
                print("Created or updated {0}".format(display_id))
            importer_id = repo.get("importer_type_id", None)
            if importer_id is not None:
                if verbose:
                    print("Adding {0} importer to {1}".format(importer_id, display_id))
                err_msg = "Failed to add {0} importer to {1}"
                with catch_server_error(err_msg.format(importer_id, display_id)):
                    server.add_importer(repo_id,
                                        importer_id,
                                        repo.get("importer_config", None))
                if verbose:
                    print("Added {0} importer to {1}".format(importer_id, display_id))
            if verbose > 1:
                print("Checking repository details for {0}".format(display_id))
                with catch_server_error("Failed to retrieve {0}".format(display_id)):
                    data = server.get_repo(repo_id)
                    print(_format_data(data))

def _cron_sync_repos(args):
    raise NotImplementedError

def _export_repos(args):
    raise NotImplementedError
