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

from .core.pulpapi import PulpServerClient
from .cli.commands import _COMMANDS, _REQUIRE_REPO_LIST

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
