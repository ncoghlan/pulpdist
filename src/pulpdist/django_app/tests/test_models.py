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
"""Basic model tests for Pulp UI Django App"""
from djangosanetesting.cases import DatabaseTestCase

from .. import models
from . import util

from django.conf import settings

class TestPulpServerModel(DatabaseTestCase):
    def setup(self):
        with util.patch_pulpapi() as api:
            server = models.PulpServer.objects.create(
                         hostname='localhost',
                         pulp_site='Nowhere',
                         server_slug='nowhere',
                         oauth_key='dummy key',
                         oauth_secret='dummy secret')
        self.pulpapi = api

    def test_api_mocked(self):
        self.pulpapi.PulpServer.assert_called()

