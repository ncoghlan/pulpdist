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
from ..core.site_config import SiteConfig
from .display import _format_data, _catch_server_error, _print_repo_table, _print_server_error

# TODO: Convert all the functions that accept an "args" parameter into methods
# of a PulpDistCommand class, with appropriate subclasses for each command.
# Include a "display()" helper method that combines print with format

def _confirm_operation(action, display_id, args):
    """Prompt the user for confirmation of action (assume OK if --force used)"""
    if args.force:
        return True
    prompt = "{0} {1}? (y/n):".format(action, display_id)
    response = raw_input(prompt)
    return response.lower() in ('y', 'yes')

def _load_site_config(args):
    """Read site config from file or server. Return value indicates if we
       read a new site config from file or not.
    """
    # TODO: This API is pretty clumsy. Will revisit when the "add" subcommand
    #       is introduced and/or everything becomes based on PulpDistCommand
    verbose = args.verbose
    config_fname = args.config_fname
    should_update_meta = False
    if config_fname is None:
        server = args.server
        if verbose:
            print("Loading configuration from host {0!r}".format(server.host))
        with _catch_server_error() as ex:
            config_data = server.get_site_config()
        if ex:
            config_data = server.get_repos()
    else:
        if verbose:
            print("Loading configuration from file {0!r}".format(config_fname))
        with open(config_fname) as config_file:
            config_data = json.load(config_file)
        should_update_meta = not isinstance(config_data, list)
    if isinstance(config_data, list):
        if verbose:
            print("Converting raw config format to site config format")
        config_data = {"RAW_TREES": config_data}
    args.site_config = SiteConfig(config_data)
    return should_update_meta

def _get_site_config(args):
    """Read the locally cached site config (loading it if not yet cached)"""
    if args.site_config is not None:
        return args.site_config
    _load_site_config(args)
    return args.site_config

def _report_empty(args):
    if args.verbose:
        print("No relevant repositories identified")

def _display_id(repo):
    """Gets a nicely formatted Repo ID from a repo configuration"""
    notes = repo["notes"].get("pulpdist")
    mirror_id = notes.get("mirror_id") if notes else None
    if mirror_id is not None:
        return "{0}({1})".format(mirror_id, notes["site_id"])
    return repo["repo_id"]

def _get_repos(args, onempty=_report_empty):
    """Get the repo configs as a list of (repo_id, display_id, repo_info) tuples

       The display_id is just a more nicely formatted alternative to the
       combined repo_id used for local mirror definitions. For raw trees, it
       is the same as repo_id.

       Optionally invokes a callback if no relevant repos are found.
       Default callback displays a message on stdout if args.verbose is set
    """
    site_config = _get_site_config(args)
    repo_configs = site_config.get_repo_configs(
        repos = args.repo_list,
        mirrors = args.mirror_list,
        trees = args.tree_list,
        sources = args.source_list,
        servers = args.server_list,
        sites = args.site_list
    )
    if not repo_configs and onempty is not None:
        onempty(args)
        return ()
    repos = [(r["repo_id"], _display_id(r), r) for r in repo_configs]
    repos.sort()
    return repos

def _get_sync_history(args, onempty=None):
    """Get the repo configs as a list of (repo_id, display_id, repo_info) tuples

       Like _get_repos, but also queries the server for the sync history of
       each repo returned.
    """
    server = args.server
    repos = _get_repos(args)
    for repo_id, display_id, repo in repos:
        history_error = "Failed to retrieve sync history for {0}".format(display_id)
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

def _validate_repos(args):
    verbose = args.verbose
    if not verbose:
        _get_site_config(args)
        return
    # Display a list of all the validated repos
    for repo_id, display_id, repo in _get_repos(args):
        print("Config for {0} is valid".format(display_id))

def _init_repos(args):
    verbose = args.verbose
    server = args.server
    update_meta = _load_site_config(args)
    if update_meta:
        if not _confirm_operation("Initialise PulpDist site", "metadata", args):
            raise RuntimeError("Cannot configure from site definition without "
                               "updating site metadata first")
        if verbose:
            print("Initialising site metadata")
        err_msg = "Failed to save PulpDist site config metadata to server"
        with _catch_server_error(err_msg) as ex:
            server.save_site_config(args.site_config.config)
        if ex: # Failed to save metadata, abort
            return -1
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
            with _catch_server_error(err_msg.format(importer_id, display_id)):
                server.add_importer(repo_id,
                                    importer_id,
                                    repo.get("importer_config", None))
            if verbose:
                print("Added {0} importer to {1}".format(importer_id, display_id))
        if verbose > 1:
            print("Checking repository details for {0}".format(display_id))
            with _catch_server_error("Failed to retrieve {0}".format(display_id)):
                data = server.get_repo(repo_id)
                print(_format_data(data))


def _list_repo_summaries(args):
    server = args.server
    repos = _get_repos(args)
    if not repos:
        return
    print("Repositories defined on {0}:".format(server.host))
    _print_repo_table("{display_name}", repos)

def _list_repo_status(args):
    server = args.server
    repos = _get_sync_history(args)
    if not repos:
        return
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
    print("Sync status for repositories on {0}".format(server.host))
    _print_repo_table("{sync_summary}", repos, headings)

def _show_sync_history(args):
    server = args.server
    for repo_id, display_id, repo in _get_sync_history(args):
        history = repo["sync_history"]
        if not history:
            print("No sync history for {0}".format(display_id))
            continue
        num_entries = args.num_entries
        if num_entries is not None:
            history = history[:num_entries]
        for sync_job in history:
            details = sync_job.get("details")
            if details and not args.showlog:
                details.pop("sync_log", None)
            print(_format_data(sync_job))

def _show_sync_log(args):
    display_success = args.success
    sync_version = "last_success" if display_success else "last_attempt"
    for repo_id, display_id, repo in _get_sync_history(args):
        sync_job = repo[sync_version]
        if sync_job is None:
            if display_success:
                err_msg = "No successful sync entry for {0}"
            else:
                err_msg = "No sync attempts for {0}"
            print(err_msg.format(display_id))
            continue
        details = sync_job["details"]
        if details is None:
            print("No sync details for {0}".format(display_id))
            continue
        msg = "Most recent sync log for {0}".format(display_id)
        header = "="*len(msg)
        print(header)
        print(msg)
        print(header)
        print(details["sync_log"])

def _show_sync_stats(args):
    # TODO: Eliminate the duplicated code between this and _show_sync_log
    display_success = args.success
    sync_version = "last_success" if display_success else "last_attempt"
    for repo_id, display_id, repo in _get_sync_history(args):
        sync_job = repo[sync_version]
        if sync_job is None:
            if display_success:
                err_msg = "No successful sync entry for {0}"
            else:
                err_msg = "No sync attempts for {0}"
            print(err_msg.format(display_id))
            continue
        summary = sync_job["summary"]
        if summary is None:
            print("No sync details for {0}".format(display_id))
            continue
        msg = "Most recent sync statistics for {0}".format(display_id)
        header = "="*len(msg)
        print(header)
        print(msg)
        print(header)
        print(_format_data(summary["stats"]))

def _list_repo_details(args):
    server = args.server
    for repo_id, display_id, repo in _get_repos(args):
        print("Repository details for {0}".format(display_id))
        with _catch_server_error("Failed to retrieve {0}".format(display_id)):
            data = server.get_repo(repo_id)
            print(_format_data(data))


# TODO: Very repetitive pattern to all these "do something to a repo" commands
# There should be some way to combine them...
# See above idea regarding a PulpDistCommand base class. That could be
# extended further here...

def _sync_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id, display_id, repo in _get_repos(args):
        if not _confirm_operation("Sync", display_id, args):
            if verbose:
                print("Not syncing {0}".format(display_id))
            continue
        if verbose:
            print("Syncing {0}".format(display_id))
        with _catch_server_error("Failed to sync {0}".format(display_id)):
            server.sync_repo(repo_id)

def _enable_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id, display_id, repo in _get_repos(args):
        if not _confirm_operation("Enable sync for", display_id, args):
            if verbose:
                print("Not enabling sync on {0}".format(display_id))
            continue
        if verbose:
            print("Enabling sync on {0}".format(display_id))
        with _catch_server_error("Failed to enable sync on {0}".format(display_id)):
            server.enable_sync(repo_id, args.dryrun)
    # TODO: Also update site metadata in the pulpdist-meta repo

def _disable_repos(args):
    verbose = args.verbose
    server = args.server
    repos = _get_repos(args)
    if not repos:
        return
    for repo_id, display_id, repo in _get_repos(args):
        if not _confirm_operation("Disable sync for", display_id, args):
            if verbose:
                print("Not disabling sync on {0}".format(display_id))
            continue
        if verbose:
            print("Disabling sync on {0}".format(display_id))
        with _catch_server_error("Failed to disable sync on {0}".format(display_id)):
            server.disable_sync(repo_id)
    # TODO: Also update site metadata in the pulpdist-meta repo

def _cron_sync_repos(args):
    raise NotImplementedError

def _delete_repos(args):
    verbose = args.verbose
    server = args.server
    repos = _get_repos(args)
    if not repos:
        return
    for repo_id, display_id, repo in _get_repos(args):
        if not _confirm_operation("Delete", display_id, args):
            if verbose:
                print("Not deleting {0}".format(display_id))
            continue
        if verbose:
            print("Deleting {0}".format(display_id))
        with _catch_server_error("Failed to delete {0}".format(display_id)):
                server.delete_repo(repo_id)
    # TODO: Also update site metadata in the pulpdist-meta repo

def _export_repos(args):
    raise NotImplementedError

def _add_config(cmd_parser):
    cmd_parser.add_argument("config_fname", metavar="CONFIG",
                            nargs="?", default=None,
                            help="A JSON file with repo config details")

def _add_entries(cmd_parser):
    cmd_parser.add_argument("-n", "--entries", metavar="NUM",
                            dest="num_entries", type=int,
                            help="Number of entries to display")

def _add_showlog(cmd_parser):
    cmd_parser.add_argument("--showlog", action='store_true',
                            help="Include the sync log in each history entry")

def _add_dryrun(cmd_parser):
    cmd_parser.add_argument("--dryrun", action='store_true',
                            help="Dry run only (don't modify local filesystem)")

def _add_success(cmd_parser):
    cmd_parser.add_argument("--success", action='store_true',
                            help="Report on most recent successful sync")

def _add_force(cmd_parser):
    cmd_parser.add_argument("--force", action='store_true',
                            help="Automatically answer yes to all prompts")

_REPO_FILTERS = (
    ("--repo",   "REPO_ID",   "repo_list", "this repo"),
    ("--mirror",   "MIRROR_ID",   "mirror_list", "this local mirror"),
    ("--site",   "SITE_ID",   "site_list", "mirrors at this site"),
    ("--tree",   "TREE_ID",   "tree_list", "mirrors of this tree"),
    ("--source", "SOURCE_ID", "source_list", "mirrors of trees from this source"),
    ("--server", "SERVER_ID", "server_list", "mirrors of trees from this server"),
)

def _add_repo_filters(cmd_parser):
    for flag, metavar, target, description in _REPO_FILTERS:
        help_msg = ("Apply operation to {} "
                    "(may be passed more than once)").format(description)
        cmd_parser.add_argument(flag, metavar=metavar, dest=target, default=[],
                                action='append', help=help_msg)


_INFO_COMMANDS = (
    ("list", _list_repo_summaries, "List repository names", ()),
    ("info", _list_repo_details, "Display repository details", ()),
    ("status", _list_repo_status, "Display repository sync status", ()),
    ("history", _show_sync_history, "Display repository sync history", [_add_entries, _add_showlog]),
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
            _add_repo_filters(cmd_parser)
            for add_arg in extra_args:
                add_arg(cmd_parser)
    # Ensure some attributes are always set
    parser.set_defaults(config_fname=None, site_config=None)

def postprocess_args(parser, args):
    # Must have already saved credentials with "pulp-admin auth login"
    pulp_host = args.pulp_host
    args.server = PulpServerClient(pulp_host)


