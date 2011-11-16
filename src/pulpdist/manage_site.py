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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# This breaks if you try to use it to run the tests via -m pulpdist.manage_site
# It seems to be an issue with the nose import emulation :P

if __name__ == "__main__":
    import os, sys
    from django.core.management import execute_from_command_line

    # Allow direct execution without stuffing up the import state...
    _pkg_dir = os.path.abspath(os.path.dirname(__file__))
    if sys.path[0] == _pkg_dir:
        sys.path[0] = os.path.dirname(_pkg_dir)
        import pulpdist

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpdist.django_site.settings")
    execute_from_command_line(sys.argv)
