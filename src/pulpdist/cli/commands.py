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
    relevant = set(args.repo_list)
    with open(args.config_fname) as repo_file:
        repo_configs = json.load(repo_file)
    for repo_config in repo_configs:
        repo_config = RepoConfig.ensure_validated(repo_config)
        repo_id = repo_config["repo_id"]
        if repo_id not in relevant:
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
                result = sync["summary"]["result"]
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
        attempt_result = last_attempt["summary"]["result"]
        attempt_time = last_attempt["started"]
        last_success = repo["last_success"]
        if last_success is None:
            success_time = "Never"
        else:
            success_time = last_success["started"]
        repo["sync_summary"] = field_format.format(success_time, attempt_time, attempt_result)
    print("Sync status for repositories on {0}".format(server.host))
    _print_repo_table("{sync_summary}", repos, headings)

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

_COMMANDS = {
    "init": _init_repos,
    "sync": _sync_repos,
    "list": _list_repo_summaries,
    "info": _list_repo_details,
    "status": _list_repo_status,
    "delete": _delete_repos,
    "validate": _validate_repos,
}

_REQUIRE_CONFIG = ["init"]

class StoreCommand(argparse.Action):
    def __call__(self, parser, namespace, cmd, option_string=None):
        namespace.command = cmd
        namespace.command_func = _COMMANDS[cmd]
        namespace.config_required = (cmd in _REQUIRE_CONFIG)


def add_parser_subcommands(parser):
    parser.add_argument("command", metavar="CMD", type=str, choices=_COMMANDS.keys(),
                        action=StoreCommand, help="The operation to perform")

def postprocess_args(parser, args):
    args.server = server = PulpServerClient(args.pulp_host)
    # Must have already saved credentials with "pulp-admin auth login"
    pulp_host = args.pulp_host
    config_fname = args.config_fname
    if args.config_required and not config_fname:
        parser.error("{0!r} command requires a configuration file".format(args.command))
    if args.repo_list:
        pass
    elif config_fname:
        with open(config_fname) as repo_file:
            if args.verbose > 1:
                print("Reading repository list from {0}".format(config_fname))
            args.repo_list = [repo["repo_id"] for repo in json.load(repo_file)]
    else:
        if args.verbose > 1:
            print("Retrieving repository list from {0}".format(pulp_host))
        args.repo_list = [repo["id"] for repo in server.get_repos()]


