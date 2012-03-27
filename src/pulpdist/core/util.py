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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""util - miscellaneous utility functions
"""

# This should be kept in sync with the version in the RPM spec file
# The suffix should be removed before creating the RPM
__version__ = "0.0.10a0"

def format_iter(iterable, fmt='{0!r}', sep=', '):
    return sep.join(fmt.format(x) for x in iterable)

def call_repr(name, args):
    return "{0}({1})".format(name, format_iter(args))

def obj_repr(obj, fields):
    name = obj.__class__.__name__
    def kwds():
        for attr in fields:
            yield "{0}={1!r}".format(attr, getattr(obj, attr))
    return "{0}({1})".format(name, format_iter(kwds()))
