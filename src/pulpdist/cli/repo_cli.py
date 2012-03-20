#!/usr/bin/env python
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

from . import commands

def make_parser():
    prog = "python -m {0}.manage_repos".format(__package__)
    description = "Manage Pulp Repositories"
    epilog = "Use '%(prog)s CMD --help' for subcommand help"
    parser = argparse.ArgumentParser(prog=prog,
                                     description=description,
                                     epilog=epilog)
    parser.add_argument("--host", metavar="HOST",
                        dest="pulp_host", default=commands.default_host(),
                        help="The Pulp server to be managed (Default: %(default)s)")
    parser.add_argument("-v", "--verbose",
                        dest="verbose", action='count',
                        help="Increase level of debugging information displayed")
    parser.add_argument("--ignoremeta", action='store_true',
                            help="Ignore any PulpDist metadata stored on the server")
    add_parser_subcommands(parser)
    return parser

def parse_args(argv):
    parser = make_parser()
    args = parser.parse_args(argv)
    return args

def main(argv):
    args = parse_args(argv)
    return args.command_factory(args)()

#===========================
# Accepted command arguments
#===========================

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
    ("list", "ShowRepoSummary", "List repository names", ()),
    ("info", "ShowRepoDetails", "Display repository details", ()),
    ("status", "ShowRepoStatus", "Display repository sync status", ()),
    ("history", "ShowSyncHistory", "Display repository sync history", [_add_entries, _add_showlog]),
    ("log", "ShowSyncLog", "Display most recent sync log", [_add_success]),
    ("stats", "ShowSyncStats", "Display most recent sync statistics", [_add_success]),
)

_SYNC_COMMANDS = (
    ("sync", "RequestSync", "Sync repositories", [_add_force]),
    ("enable", "EnableSync", "Set repositories to accept sync commands", [_add_force, _add_dryrun]),
    ("disable", "DisableSync", "Set repositories to ignore sync commands", [_add_force]),
    ("cron_sync", "_cron_sync_repos", "(NYI) Selectively sync repositories based on metadata", ()),
)

_REPO_COMMANDS = (
    ("validate", "ValidateRepoConfig", "Validate repository configuration", [_add_config]),
    ("init", "InitialiseRepos", "Create or overwrite repositories", [_add_config, _add_force]),
    ("delete", "DeleteRepo", "Delete repositories", [_add_force]),
    ("export", "_export_repos", "(NYI) Export repository configuration", [_add_config]),
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
    names = globals()
    for title, subcommands in _COMMANDS:
        for name, factory, cmd_help, extra_args in subcommands:
            cmd_parser = subparsers.add_parser(name, help=cmd_help)
            cmd_parser.set_defaults(command_factory=getattr(commands, factory))
            _add_repo_filters(cmd_parser)
            for add_arg in extra_args:
                add_arg(cmd_parser)
    # Ensure some attributes are always set
    parser.set_defaults(config_fname=None)

