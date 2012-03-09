#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""Helpers for tests that need to access a real Pulp server back end"""

import socket

from .. import pulpapi
from .compat import unittest

# Required setup on local machine to run pulpapi tests
#
# - Pulp instance running on default port (i.e. 80)
# - default admin/admin account still in place
# - OAuth enabled with keys as seen below
# - "pulp-admin auth login --username admin --password admin"

# These utilities are defined here to avoid cross dependencies between tests
# that need them, but, to keep the core tests simple only the CLI and Plugin
# tests actually use them.

class PulpTestCase(unittest.TestCase):
    REPO_ID = u"test_repo"

    def setUp(self):
        self.server = self.local_test_server()

    def local_test_server(self):
        localhost = socket.gethostname()
        oauth_key = "example-oauth-key"
        oauth_secret = "example-oauth-secret"
        return pulpapi.PulpServer(localhost, oauth_key, oauth_secret)

    def local_test_repo(self):
        try:
            self.server.delete_repo(self.REPO_ID)
        except pulpapi.ServerRequestError:
            pass
        else:
            raise RuntimeError("Previous test run didn't destroy test repo!")
        return self.server.create_repo(self.REPO_ID)

    def assertServerRequestError(self, *args, **kwds):
        return self.assertRaises(pulpapi.ServerRequestError, *args, **kwds)

class BasicAuthMixin(object):
    def _local_test_server(self):
        localhost = socket.gethostname()
        username = "admin"
        password = "admin"
        return pulpapi.PulpServerClient(localhost,
                                        username, password)

class LocalCertMixin(object):
    def _local_test_server(self):
        localhost = socket.gethostname()
        return pulpapi.PulpServerClient(localhost)

if __name__ == '__main__':
    unittest.main()
