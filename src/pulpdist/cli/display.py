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
from operator import itemgetter

from ..core.pulpapi import ServerRequestError

_id_key = itemgetter("repo_id")

# TODO: Get rid of most of the leading underscores (which predate creation
# of a separate display module)

def _id_field_width(repos):
    return max(map(len, map(_id_key, repos))) + 3

def _print_repo_table(field_format, repos, header=None):
    id_width = _id_field_width(repos)
    if header is not None:
        print("{1:{0}.{0}}{2}".format(id_width, "Repo ID", header))
    row_format = "{1:{0}.{0}}" + field_format
    for repo in sorted(repos, key=_id_key):
        notes = repo["notes"].get("pulpdist")
        mirror_id = notes.get("mirror_id") if notes else None
        if mirror_id is None:
            repo_id = repo["repo_id"]
        else:
            repo_id = "{0}({1})".format(mirror_id, notes["site_id"])
        print(row_format.format(id_width, repo_id, **repo))


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
def _catch_server_error(msg=None):
    """Displays msg if a server error occurs.

       Returns a list object on entry. If an exception occurs, it is
       appended to the list, making it easy to take additional action in
       the event of an error::

           with _catch_server_error(msg) as ex:
               # Access Pulp server
           if ex:
              details = ex[0]
              # Additional processing in response to the exception

    """
    caught_expection = []
    try:
        yield caught_expection
    except ServerRequestError, ex:
        caught_expection.append(ex)
        if msg is not None:
            _print_server_error(msg, ex)

