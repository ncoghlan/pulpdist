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
"""HTTP Access Tests for Pulp Web UI"""
from contextlib import contextmanager

from djangosanetesting.cases import HttpTestCase

from .. import settings
from ...django_app import util

# Note: needs a live Pulp server to back the web API

@contextmanager
def site_login(client, username):
    login_status = client.login(username=username)
    try:
        yield login_status
    finally:
        client.logout()

def user_login(client):
    return site_login(client, settings.DUMMY_AUTH_USER)

def staff_login(client):
    return site_login(client, settings.DUMMY_AUTH_STAFF)

def su_login(client):
    return site_login(client, settings.DUMMY_AUTH_SUPER)


class TestSiteIndex(HttpTestCase):
    fixtures = ["pulpdist/fixtures/pulpdist_server_details.json"]

    def test_index_loads(self):
        with user_login(self.client) as logged_in:
            self.assertTrue(logged_in)
            resp = self.client.get("/pulpdist/")
            self.assertEqual(resp.status_code, 200)

    def test_root_redirect(self):
        resp = self.client.get("")
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp["Location"].endswith("/pulpdist/"))

    def test_version_display(self):
        # This is part of the base template, we check the login page
        # so we don't need to log in first
        resp = self.client.get("/pulpdist/login/")
        self.assertIn(util.version(), resp.content)
