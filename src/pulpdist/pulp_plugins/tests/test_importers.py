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

"""Basic test suite for sync transfer plugins"""
import unittest
import socket

from ...core import pulpapi, sync_trees
from ...core.tests import example_trees

IMPORTERS = ["simple_tree", "versioned_tree", "snapshot_tree", "delta_tree", "snapshot_delta"]

class PulpTestCase(unittest.TestCase):
    def setUp(self):
        localhost = socket.gethostname()
        oauth_key = "example-oauth-key"
        oauth_secret = "example-oauth-secret"
        self.server = pulpapi.PulpServer(localhost, oauth_key, oauth_secret)


class TestConfiguration(PulpTestCase):
    # Test configuration of importers without
    # actually trying to sync anything
    def test_importers_loaded(self):
       importers = self.server.get_generic_importers()
       expected = set(IMPORTERS)
       for importer in importers:
           expected.remove(importer["id"])
       if expected:
           self.fail("Missing expected importers: {}".format(list(expected)))

class TestSyncTree(example_trees.TreeTestCase):

    def test_sync(self):
        local_path = self.local_path
        params = self.params
        params.update(example_trees.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        task.run_sync()
        self.check_tree_layout(local_path)


if __name__ == '__main__':
    unittest.main()
