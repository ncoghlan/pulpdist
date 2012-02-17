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

from .cli.commands import add_parser_subcommands, postprocess_args

def make_parser():
    prog = "python -m {0}.manage_repos".format(__package__)
    description = "Manage Pulp Repositories"
    epilog = "Use '%(prog)s CMD --help' for subcommand help"
    parser = argparse.ArgumentParser(prog=prog,
                                     description=description,
                                     epilog=epilog)
    parser.add_argument("--repo", metavar="REPO_ID",
                        dest="repo_list", action='append',
                        help="Apply requested operation to this repo "
                             "(may be specified multiple times)")
    parser.add_argument("--host", metavar="HOST",
                        dest="pulp_host", default=socket.getfqdn(),
                        help="The Pulp server to be managed (Default: %(default)s)")
    parser.add_argument("-v", "--verbose",
                        dest="verbose", action='count',
                        help="Increase level of debugging information displayed")
    add_parser_subcommands(parser)
    return parser

def parse_args(argv):
    parser = make_parser()
    args = parser.parse_args(argv)
    postprocess_args(parser, args)
    return args

def main(argv):
    args = parse_args(argv)
    args.command_func(args)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
