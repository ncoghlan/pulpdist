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

try:
    import pulpdist
except ImportError:
    # Allow running from source checkout
    import sys
    import os.path
    _this = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_this, "..", "src"))
    sys.path.insert(0, _src_dir)

from pulpdist.core.pulpapi import PulpServerClient

def _make_parser():
    description="Synchronise Pulp Repositories"
    epilog = ("The expected JSON file format is a top level list containing "
              "mappings with a 'repo_id' attribute. Any other fields are "
              "ignored.")
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument("pulp_host", metavar="HOST", type=str,
                    help="The Pulp server with the repos to be synchronised")
    parser.add_argument("repo_fname", metavar="REPO_LIST", type=str, nargs="?",
                    help="A JSON file identifying repos to synchronise")
    return parser

def _main(argv):
    args = _make_parser().parse_args(argv)
    # Must have already saved credentials with "pulp-admin auth login"
    pulp_host = args.pulp_host
    server = PulpServerClient(pulp_host)
    repo_fname = args.repo_fname
    if repo_fname:
        with open(repo_fname) as repo_file:
            print("Reading repository list from {0!r}".format(repo_fname))
            repo_list = [repo["repo_id"] for repo in json.load(repo_file)]
    else:
        print("Retrieving repository list from {0!r}".format(pulp_host))
        repo_list = [repo["id"] for repo in server.get_repos()]
    for repo_id in repo_list:
        print("Syncing {0}".format(repo_id))
        server.sync_repo(repo_id)


if __name__ == "__main__":
    import sys
    _main(sys.argv[1:])
