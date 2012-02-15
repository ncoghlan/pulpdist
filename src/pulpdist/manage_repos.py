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
import sys
import contextlib

try:
    import pulpdist
except ImportError:
    # Allow running from source checkout
    import os.path
    _this = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_this, "..", "src"))
    sys.path.insert(0, _src_dir)

from pulpdist.core.pulpapi import PulpServerClient, ServerRequestError
from pulpdist.core.repo_config import RepoConfig

def _format_data(data, prefix=0, indent=2):
    out = json.dumps(data, indent=indent)
    if prefix:
        out = "\n".join(prefix * " " + line for line in out.splitlines())
    return out

def _print_server_error(msg, ex):
    details = "{0} ({1})\n".format(msg, ex)
    sys.stderr.write(details)
    sys.stderr.flush()

@contextlib.contextmanager
def _catch_server_error(msg):
    try:
        yield
    except ServerRequestError, ex:
        _print_server_error(msg, ex)

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
    with open(args.repo_fname) as repo_file:
        repo_configs = json.load(repo_file)
    for repo_config in repo_configs:
        repo_config = RepoConfig.ensure_validated(repo_config)
        repo_id = repo_config["repo_id"]
        if verbose:
            print("Creating {0}".format(repo_id))
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
            msg = "Failed to create {0}".format(repo_id)
            _print_server_error(msg, ex)
            continue
        if verbose:
            print("Created {0}".format(repo_id))
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

def _list_repos(args):
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
        if verbose:
            print("Syncing {0}".format(repo_id))
        with _catch_server_error("Failed to sync {0}".format(repo_id)):
            server.sync_repo(repo_id)

def _delete_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        response = raw_input("Delete {0}? (y/n):".format(repo_id))
        delete = response.lower() == 'y'
        if delete:
            if verbose:
                print("Deleting {0}".format(repo_id))
            with _catch_server_error("Failed to delete {0}".format(repo_id)):
                    server.delete_repo(repo_id)
        elif verbose:
            print("Not deleting {0}".format(repo_id))

_COMMANDS = {
    "init": _init_repos,
    "sync": _sync_repos,
    "list": _list_repos,
    "delete": _delete_repos,
    "validate": _validate_repos,
}

_REQUIRE_REPO_LIST = ["init"]

class StoreCommand(argparse.Action):
    def __call__(self, parser, namespace, cmd, option_string=None):
        namespace.command = cmd
        namespace.fetch_repo_list = (cmd not in _REQUIRE_REPO_LIST)

def _make_parser():
    description="Manage Pulp Repositories"
    epilog = ("The expected JSON file format is a top level list containing "
              "mappings with a 'repo_id' attribute. Any other fields are "
              "only processed by the 'init' command.")
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument("-v", "--verbose", dest="verbose", action='count',
                        help="Increase level of debugging information displayed")
    parser.add_argument("-f", "--file", metavar="REPO_LIST", dest="repo_fname", type=str,
                        help="A JSON file identifying repos to manage")
    parser.add_argument("pulp_host", metavar="HOST", type=str,
                        help="The Pulp server with the repos to be synchronised")
    parser.add_argument("command", metavar="CMD", type=str, choices=_COMMANDS.keys(),
                        action=StoreCommand, help="The operation to perform")
    return parser

def _parse_args(argv):
    parser = _make_parser()
    args = parser.parse_args(argv)
    args.server = server = PulpServerClient(args.pulp_host)
    # Must have already saved credentials with "pulp-admin auth login"
    pulp_host = args.pulp_host
    repo_fname = args.repo_fname
    if repo_fname:
        with open(repo_fname) as repo_file:
            if args.verbose:
                print("Reading repository list from {0}".format(repo_fname))
            args.repo_list = [repo["repo_id"] for repo in json.load(repo_file)]
    elif args.fetch_repo_list:
        if args.verbose:
            print("Retrieving repository list from {0}".format(pulp_host))
        args.repo_list = [repo["id"] for repo in server.get_repos()]
    else:
        parser.error("{0} command requires an explicit repo list".format(args.command))
    return args

def _main(argv):
    args = _parse_args(argv)
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
