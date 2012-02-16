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

import json
import sys
import contextlib

from ..core.pulpapi import ServerRequestError

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

