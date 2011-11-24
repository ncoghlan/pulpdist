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

def _local_test_server():
    localhost = socket.gethostname()
    oauth_key = "example-oauth-key"
    oauth_secret = "example-oauth-secret"
    return pulpapi.PulpServer(localhost, oauth_key, oauth_secret)

class PulpTestCase(unittest.TestCase):
    def setUp(self):
        self.server = _local_test_server()

class TestServerAccess(PulpTestCase):
    # Test basic access to the local Pulp server
    # including whether or not the pulpdist plugins
    # are installed correctly
    REPO_ID = "test_repo"

    def test_importers_loaded(self):
       importers = self.server.get_generic_importers()
       expected = set(IMPORTERS)
       for importer in importers:
           expected.remove(importer["id"])
       if expected:
           self.fail("Missing expected importers: {}".format(list(expected)))

    def test_missing_repo(self):
        with self.assertRaises(pulpapi.ServerRequestError) as details:
            self.server.get_repo(self.REPO_ID)
        exc = details.exception
        self.assertEqual(exc.args[0], 404)

    def test_create_and_delete_repo(self):
        repo_id = self.REPO_ID
        repo_name = "Test Repo"
        description = "This is a test repo!"
        repo = self.server.create_repo(repo_id, repo_name, description)
        self.assertTrue(self.server.delete_repo(repo_id))
        self.assertEqual(repo["id"], repo_id)
        self.assertEqual(repo["display_name"], repo_name)
        self.assertEqual(repo["description"], description)
        # Ensure it is really gone
        with self.assertRaises(pulpapi.ServerRequestError) as details:
            self.server.get_repo(self.REPO_ID)
        exc = details.exception
        self.assertEqual(exc.args[0], 404)

class TestConfiguration(PulpTestCase):
    # Test configuration of importers without
    # actually trying to sync anything
    REPO_ID = "test_repo"
    def setUp(self):
        super(TestConfiguration, self).setUp()
        self.repo = self.server.create_repo(self.REPO_ID)

    def tearDown(self):
        self.server.delete_repo(self.repo["id"])

    def check_importer(self, imp, repo_id, importer_id, params):
        self.assertEqual(imp["config"], params)
        self.assertEqual(imp["repo_id"], repo_id)
        self.assertEqual(imp["id"], importer_id)
        self.assertEqual(imp["importer_type_id"], importer_id)
        self.assertFalse(imp["sync_in_progress"])
        self.assertIs(imp["last_sync"], None)
        self.check_get_importer(repo_id, imp)

    def check_get_importer(self, repo_id, imp):
        importers = self.server.get_importers(repo_id)
        self.assertEqual(len(importers), 1)
        self.assertEqual(importers[0], imp)

    def test_no_importer(self):
        repo_id = self.repo["id"]
        self.assertEqual(self.server.get_importers(repo_id), [])

    def test_simple_tree(self):
        params = example_trees.CONFIG_TREE_SYNC.copy()
        params['local_path'] = 'test_path'
        repo_id = self.repo["id"]
        importer_id = 'simple_tree'
        imp = self.server.add_importer(repo_id, importer_id, params)
        self.check_importer(imp, repo_id, importer_id, params)

    def test_versioned_tree(self):
        params = example_trees.CONFIG_VERSIONED_SYNC.copy()
        params['local_path'] = 'test_path'
        repo_id = self.repo["id"]
        importer_id = 'versioned_tree'
        imp = self.server.add_importer(repo_id, importer_id, params)
        self.check_importer(imp, repo_id, importer_id, params)

    def test_snapshot_tree(self):
        params = example_trees.CONFIG_SNAPSHOT_SYNC.copy()
        params['local_path'] = 'test_path'
        repo_id = self.repo["id"]
        importer_id = 'versioned_tree'
        imp = self.server.add_importer(repo_id, importer_id, params)
        self.check_importer(imp, repo_id, importer_id, params)


if __name__ == '__main__':
    unittest.main()
