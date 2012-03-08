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

import json
import sys
import contextlib
import collections

from ..core.pulpapi import ServerRequestError

def print_msg(_fmt, *args, **kwds):
    """Prints a formatted message to sys.stdout"""
    print(_fmt.format(*args, **kwds))

def print_header(_fmt, *args, **kwds):
    """Prints a formatted message to sys.stdout as a prominent header"""
    msg = _fmt.format(*args, **kwds)
    header = "="*len(msg)
    print(header)
    print(msg)
    print(header)

def format_data(data, prefix=0, indent=2):
    """Serialises data as JSON with an optional uniform leading indent"""
    out = json.dumps(data, indent=indent)
    if prefix:
        out = "\n".join(prefix * " " + line for line in out.splitlines())
    return out

def print_data(*args, **kwds):
    """Prints JSON formatted data to sys.stdout"""
    print(format_data(*args, **kwds))

def _id_field_width(repos):
    id_widths = (len(repo.display_id) for repo in repos)
    return max(id_widths) + 3

def print_repo_table(field_format, repos, header=None):
    """Displays info from site_config.PulpRepo entries as a table"""
    id_width = _id_field_width(repos)
    if header is not None:
        print_msg("{1:{0}.{0}}{2}", id_width, "Repo ID", header)
    row_format = "{1:{0}.{0}}" + field_format
    for repo in repos:
        print_msg(row_format, id_width, repo.display_id, **repo.config)


def print_server_error(msg, ex):
    """Write a Pulp server """
    details = "{0} ({1})\n".format(msg, ex)
    sys.stderr.write(details)
    sys.stderr.flush()

@contextlib.contextmanager
def catch_server_error(_fmt=None, *args, **kwds):
    """Catches and suppresses Pulp API server errors

       Displays a formatted message if a Pulp server error occurs.

       Returns a list object on entry. If an exception occurs, it is
       appended to the list, making it easy to take additional action in
       the event of an error::

           with _catch_server_error(msg) as ex:
               # Access Pulp server
           if ex:
              details = ex[0]
              # Additional processing in response to the exception

    """
    msg = _fmt.format(args, kwds) if _fmt is not None else None
    caught_expection = []
    try:
        yield caught_expection
    except ServerRequestError, ex:
        caught_expection.append(ex)
        if msg is not None:
            print_server_error(msg, ex)

