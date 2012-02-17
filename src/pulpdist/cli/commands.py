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
from .display import _format_data, _catch_server_error, _print_repo_table

def _confirm_operation(action, repo_id, args):
    if args.force:
        return True
    prompt = "{0} {1}? (y/n):".format(action, repo_id)
    response = raw_input(prompt)
    return response.lower() in ('y', 'yes')

def _validate_repos(args):
    verbose = args.verbose
    with open(args.repo_fname) as repo_file:
        repo_configs = json.load(repo_file)
    for repo_config in repo_configs:
        repo_id = repo_config["repo_id"]
        if verbose:
            print("Validating config for {0}".format(repo_id))
        repo_config = RepoConfig.ensure_validated(repo_config)
        if verbose:
            print("  Config for {0} is valid".format(repo_id))

def _init_repos(args):
    verbose = args.verbose
    server = args.server
    repo_list = args.repo_list
    if repo_list is not None:
        relevant = set(repo_list)
        def _is_relevant(repo_id):
            return repo_id in relevant
    else:
        def _is_relevant(repo_id):
            return True
    with open(args.config_fname) as repo_file:
        repo_configs = json.load(repo_file)
    for repo_config in repo_configs:
        repo_config = RepoConfig.ensure_validated(repo_config)
        repo_id = repo_config["repo_id"]
        if not _is_relevant(repo_id):
            if verbose > 1:
                print("Skipping {0}".format(repo_id))
            continue
        if not _confirm_operation("Initialise", repo_id, args):
            if verbose:
                print("Not initialising {0}".format(repo_id))
            continue
        if verbose:
            print("Creating or updating {0}".format(repo_id))
        if verbose > 1:
            print("Configuration:")
            print(_format_data(repo_config))
        try:
            server.create_or_save_repo(
                repo_id,
                repo_config.get("display_name", None),
                repo_config.get("description", None),
                repo_config.get("notes", None))
        except ServerRequestError, ex:
            msg = "Failed to create or update {0}".format(repo_id)
            _print_server_error(msg, ex)
            continue
        if verbose:
            print("Created or updated {0}".format(repo_id))
        importer_id = repo_config.get("importer_type_id", None)
        if importer_id is not None:
            if verbose:
                print("Adding {0} importer to {1}".format(importer_id, repo_id))
            err_msg = "Failed to add {0} importer to {1}"
            with _catch_server_error(err_msg.format(importer_id, repo_id)):
                server.add_importer(repo_id,
                                    importer_id,
                                    repo_config.get("importer_config", None))
            if verbose:
                print("Added {0} importer to {1}".format(importer_id, repo_id))
        if verbose > 1:
            print("Checking repository details for {0}".format(repo_id))
            with _catch_server_error("Failed to retrieve {0}".format(repo_id)):
                data = server.get_repo(repo_id)
                print(_format_data(data))


def _all_repo_details(server, repo_ids):
    repos = []
    for repo_id in repo_ids:
        with _catch_server_error("Failed to retrieve {0}".format(repo_id)):
            repo = server.get_repo(repo_id)
            repos.append(repo)
    return repos

def _list_repo_summaries(args):
    server = args.server
    repos = _all_repo_details(server, args.repo_list)
    if not repos:
        print("No repositories defined on {0}".format(server.host))
        return
    print("Repositories defined on {0}:".format(server.host))
    _print_repo_table("{display_name}", repos)

def _all_sync_history(server, repo_ids):
    repos = _all_repo_details(server, repo_ids)
    for repo in repos:
        repo_id = repo["id"]
        history_error = "Failed to retrieve sync history for {0}".format(repo_id)
        repo["sync_history"] = None
        repo["last_attempt"] = None
        repo["last_success"] = None
        with _catch_server_error(history_error):
            repo["sync_history"] = history = server.get_sync_history(repo_id)
            if not history:
                continue
            repo["last_attempt"] = history[0]
            for sync in history:
                summary = sync["summary"]
                if summary is None:
                    continue
                result = summary["result"]
                if result in "SYNC_COMPLETED SYNC_UP_TO_DATE".split():
                    repo["last_success"] = sync
                    break
    return repos

def _list_repo_status(args):
    server = args.server
    repos = _all_sync_history(server, args.repo_list)
    if not repos:
        print("No repositories defined on {0}".format(server.host))
        return
    field_format = "{0:30}{1:30}{2}"
    headings = field_format.format("Last Sync", "Last Attempt", "Last Result")
    for repo in repos:
        repo_id = repo["id"]
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
    print("Sync status for repositories on {0}".format(server.host))
    _print_repo_table("{sync_summary}", repos, headings)

def _show_sync_history(args):
    server = args.server
    repos = _all_sync_history(server, args.repo_list)
    if not repos:
        print("No repositories defined on {0}".format(server.host))
        return
    for repo in repos:
        repo_id = repo["id"]
        history = repo["sync_history"]
        if not history:
            print("No sync history for {0}".format(repo_id))
            continue
        num_entries = args.num_entries
        if num_entries is not None:
            history = history[:num_entries]
        for sync_job in history:
            print(_format_data(sync_job))

def _show_sync_log(args):
    server = args.server
    repos = _all_sync_history(server, args.repo_list)
    if not repos:
        print("No repositories defined on {0}".format(server.host))
        return
    display_success = args.success
    sync_version = "last_success" if display_success else "last_attempt"
    for repo in repos:
        repo_id = repo["id"]
        sync_job = repo[sync_version]
        if sync_job is None:
            if display_success:
                err_msg = "No successful sync entry for {0}"
            else:
                err_msg = "No sync attempts for {0}"
            print(err_msg.format(repo_id))
            continue
        details = sync_job["details"]
        if details is None:
            print("No sync details for {0}".format(repo_id))
            continue
        msg = "Most recent sync log for {0}".format(repo_id)
        header = "="*len(msg)
        print(header)
        print(msg)
        print(header)
        print(details["sync_log"])

def _show_sync_stats(args):
    # TODO: Eliminate the duplicated code between this and _show_sync_log
    server = args.server
    repos = _all_sync_history(server, args.repo_list)
    if not repos:
        print("No repositories defined on {0}".format(server.host))
        return
    display_success = args.success
    sync_version = "last_success" if display_success else "last_attempt"
    for repo in repos:
        repo_id = repo["id"]
        sync_job = repo[sync_version]
        if sync_job is None:
            if display_success:
                err_msg = "No successful sync entry for {0}"
            else:
                err_msg = "No sync attempts for {0}"
            print(err_msg.format(repo_id))
            continue
        summary = sync_job["summary"]
        if summary is None:
            print("No sync details for {0}".format(repo_id))
            continue
        msg = "Most recent sync statistics for {0}".format(repo_id)
        header = "="*len(msg)
        print(header)
        print(msg)
        print(header)
        print(_format_data(summary["stats"]))

def _list_repo_details(args):
    server = args.server
    for repo_id in args.repo_list:
        print("Repository details for {0}".format(repo_id))
        with _catch_server_error("Failed to retrieve {0}".format(repo_id)):
            data = server.get_repo(repo_id)
            print(_format_data(data))

def _sync_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        if not _confirm_operation("Sync", repo_id, args):
            if verbose:
                print("Not syncing {0}".format(repo_id))
            continue
        if verbose:
            print("Syncing {0}".format(repo_id))
        with _catch_server_error("Failed to sync {0}".format(repo_id)):
            server.sync_repo(repo_id)

def _enable_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        if not _confirm_operation("Enable sync for", repo_id, args):
            if verbose:
                print("Not enabling sync on {0}".format(repo_id))
            continue
        if verbose:
            print("Enabling sync on {0}".format(repo_id))
        with _catch_server_error("Failed to enable sync on {0}".format(repo_id)):
            server.enable_sync(repo_id, args.dryrun)

def _disable_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        if verbose:
            print("Disabling sync on {0}".format(repo_id))
        with _catch_server_error("Failed to disable sync on {0}".format(repo_id)):
            server.disable_sync(repo_id)

def _cron_sync_repos(args):
    raise NotImplementedError

def _delete_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        if not _confirm_operation("Delete", repo_id, args):
            if verbose:
                print("Not deleting {0}".format(repo_id))
            continue
        if verbose:
            print("Deleting {0}".format(repo_id))
        with _catch_server_error("Failed to delete {0}".format(repo_id)):
                server.delete_repo(repo_id)

def _export_repos(args):
    raise NotImplementedError

def _add_config(cmd_parser):
    cmd_parser.add_argument("config_fname", metavar="CONFIG",
                            help="A JSON file with repo config details")

def _add_entries(cmd_parser):
    cmd_parser.add_argument("-n", "--entries", metavar="NUM",
                            dest="num_entries", type=int,
                            help="Number of entries to display")

def _add_dryrun(cmd_parser):
    cmd_parser.add_argument("--dryrun", action='store_true',
                            help="Dry run only (don't modify local filesystem)")

def _add_success(cmd_parser):
    cmd_parser.add_argument("--success", action='store_true',
                            help="Report on most recent successful sync")

def _add_force(cmd_parser):
    cmd_parser.add_argument("--force", action='store_true',
                            help="Automatically answer yes to all prompts")

_INFO_COMMANDS = (
    ("list", _list_repo_summaries, "List repository names", ()),
    ("info", _list_repo_details, "Display repository details", ()),
    ("status", _list_repo_status, "Display repository sync status", ()),
    ("history", _show_sync_history, "Display repository sync history", [_add_entries]),
    ("sync_log", _show_sync_log, "Display most recent sync log", [_add_success]),
    ("sync_stats", _show_sync_stats, "Display most recent sync statistics", [_add_success]),
)

_SYNC_COMMANDS = (
    ("sync", _sync_repos, "Sync repositories", [_add_force]),
    ("enable", _enable_repos, "Set repositories to accept sync commands", [_add_force, _add_dryrun]),
    ("disable", _disable_repos, "Set repositories to ignore sync commands", [_add_force]),
    ("cron_sync", _cron_sync_repos, "(NYI) Selectively sync repositories based on metadata", ()),
)

_REPO_COMMANDS = (
    ("validate", _validate_repos, "Validate repository configuration", [_add_config]),
    ("init", _init_repos, "Create or update repositories", [_add_config, _add_force]),
    ("delete", _delete_repos, "Delete repositories", [_add_force]),
    ("export", _export_repos, "(NYI) Export repository configuration", [_add_config]),
)

_COMMANDS = (
    ("Synchronisation Management", _SYNC_COMMANDS),
    ("Status Queries", _INFO_COMMANDS),
    ("Repository Management", _REPO_COMMANDS),
)

def add_parser_subcommands(parser):
    # Add categorised subparsers
    #   Alas, argparse doesn't let us group the subcommands, so we add the
    #   alternatives as one big list (see http://bugs.python.org/issue14037)
    subparsers = parser.add_subparsers(title="Repository Commands")
    for title, subcommands in _COMMANDS:
        for name, func, cmd_help, extra_args in subcommands:
            cmd_parser = subparsers.add_parser(name, help=cmd_help)
            cmd_parser.set_defaults(command_func=func)
            for add_arg in extra_args:
                add_arg(cmd_parser)
    # Ensure config_fname is always set, even for commands that don't need it
    parser.set_defaults(config_fname=None)

def postprocess_args(parser, args):
    # Must have already saved credentials with "pulp-admin auth login"
    pulp_host = args.pulp_host
    args.server = server = PulpServerClient(pulp_host)
    # If the command doesn't accept a config file, and there's no repo
    # list specified, apply the operation to every repo on the server
    if args.config_fname is None and not args.repo_list:
        if args.verbose > 1:
            print("Retrieving repository list from {0}".format(pulp_host))
        args.repo_list = [repo["id"] for repo in server.get_repos()]


