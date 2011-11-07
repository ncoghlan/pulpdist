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
"""Utility functions for Django Pulp UI unit tests"""

import mock
from .. import models

# We make it easy to mock pulpapi in the models file
# so we don't need a live Pulp server for the unit tests.
# The Pulp Web UI integration tests take care of checking
# how well we align with the *real* server API.
def patch_pulpapi():
    """Mock out pulpapi in the django_pulpdist models file"""
    name = models.__name__ + '.pulpapi'
    return mock.patch(name)
