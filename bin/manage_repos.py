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
import pprint

def _display_error(msg):
    sys.stderr.write(msg+'\n')
    sys.stderr.flush()

try:
    import pulpdist
except ImportError:
    # Allow running from source checkout
    import os.path
    _this = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_this, "..", "src"))
    sys.path.insert(0, _src_dir)

from pulpdist.core.pulpapi import PulpServerClient, ServerRequestError

def _init_repos(args):
    raise NotImplemented # TODO: Bring over from init_repos.py

def _list_repos(args):
    server = args.server
    for repo_id in args.repo_list:
        print("Repository details for: {0}".format(repo_id))
        try:
            data = server.get_repo(repo_id)
        except ServerRequestError, ex:
            _display_error("Failed to sync {0} ({1})", repo_id, ex)
        else:
            pprint.pprint(data)

def _sync_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        if verbose:
            print("Syncing {0}".format(repo_id))
        try:
            server.sync_repo(repo_id)
        except ServerRequestError, ex:
            _display_error("Failed to sync {0} ({1})", repo_id, ex)

def _delete_repos(args):
    verbose = args.verbose
    server = args.server
    for repo_id in args.repo_list:
        response = raw_input("Delete {0}? (y/n):".format(repo_id))
        delete = response.lower() == 'y'
        if delete:
            if verbose:
                print("Deleting {0}".format(repo_id))
            try:
                server.delete_repo(repo_id)
            except ServerRequestError, ex:
                _display_error("Failed to delete {0} ({1})", repo_id, ex)
        elif verbose:
            print("Not deleting {0}".format(repo_id))

_COMMANDS = {
    "init": _init_repos,
    "sync": _sync_repos,
    "list": _list_repos,
    "delete": _delete_repos,
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
                print("Reading repository list from {0!r}".format(repo_fname))
            args.repo_list = [repo["repo_id"] for repo in json.load(repo_file)]
    elif args.fetch_repo_list:
        if args.verbose:
            print("Retrieving repository list from {0!r}".format(pulp_host))
        args.repo_list = [repo["id"] for repo in server.get_repos()]
    else:
        parser.error("{0!r} command requires an explicit repo list".format(args.command))
    return args

def _main(argv):
    args = _parse_args(argv)
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
