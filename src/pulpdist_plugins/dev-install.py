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

"""dev-install - link the pulpdist plugins into an installed Pulp instance"""

import os

PULP_INSTALL_PREFIX = "/var/lib/pulp/plugins"

TYPE_SPEC = "types/pulpdist.json"
IMPORTER = "importers/pulpdist_importers"
DISTRIBUTOR = "distributors/pulpdist_distributors"

LINKS = (TYPE_SPEC, IMPORTER, DISTRIBUTOR)

def link_names():
    for target in LINKS:
        link_target = os.path.abspath(target)
        link_origin = os.path.join(PULP_INSTALL_PREFIX, target)
        print ("{} -> {}".format(link_origin, link_target))
        os.symlink(link_target, link_origin)

def unlink_names():
    for target in LINKS:
        link_origin = os.path.join(PULP_INSTALL_PREFIX, target)
        if not os.path.lexists(link_origin):
            print("{} does not exist, skipping".format(link_origin))
            continue
        if not os.path.islink(link_origin):
            print("{} is not a symlink, skipping".format(link_origin))
            continue
        link_target = os.readlink(link_origin)
        print ("Unlinking {} from {}".format(link_origin, link_target))
        os.unlink(link_origin)

if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--install"]:
        print "Installing symlinks"
        link_names()
    else:
        print "Removing symlinks"
        unlink_names()
