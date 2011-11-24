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
import time

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

    def _add_importer(self, importer_id, params):
        params['local_path'] = 'test_path'
        repo_id = self.repo["id"]
        return self.server.add_importer(repo_id, importer_id, params)

    def check_importer(self, imp, importer_id, params):
        repo_id = self.repo["id"]
        self.assertEqual(imp["config"], params)
        self.assertEqual(imp["repo_id"], repo_id)
        self.assertEqual(imp["id"], importer_id)
        self.assertEqual(imp["importer_type_id"], importer_id)
        self.assertFalse(imp["sync_in_progress"])
        self.assertIsNone(imp["last_sync"])
        self.check_get_importer(repo_id, imp)

    def check_get_importer(self, repo_id, imp):
        importers = self.server.get_importers(repo_id)
        self.assertEqual(len(importers), 1)
        self.assertEqual(importers[0], imp)

    def test_no_importer(self):
        repo_id = self.repo["id"]
        self.assertEqual(self.server.get_importers(repo_id), [])

    def test_simple_tree(self):
        importer_id = 'simple_tree'
        params = example_trees.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_versioned_tree(self):
        importer_id = 'versioned_tree'
        params = example_trees.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_snapshot_tree(self):
        importer_id = 'snapshot_tree'
        params = example_trees.CONFIG_SNAPSHOT_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

class TestLocalSync(example_trees.TreeTestCase):
    # Actually test synchronisation
    REPO_ID = "test_repo"

    def setUp(self):
        super(TestLocalSync, self).setUp()
        self.server = _local_test_server()
        self.repo = self.server.create_repo(self.REPO_ID)

    def tearDown(self):
        self.server.delete_repo(self.repo["id"])

    def _add_importer(self, importer_id, params):
        params.update(self.params)
        repo_id = self.repo["id"]
        return self.server.add_importer(repo_id, importer_id, params)

    def _get_importer(self):
        return self.server.get_importer(self.repo["id"])

    def _sync_repo(self):
        return self.server.sync_repo(self.repo["id"])

    def _wait_for_sync(self):
        deadline = time.time() + 10
        sync_started = False
        while time.time() < deadline:
            imp = self._get_importer()
            if imp["last_sync"] is not None:
                break
            if sync_started:
                self.assertTrue(imp["sync_in_progress"])
            else:
                sync_started = imp["sync_in_progress"]
        else:
            self.fail("Timed out waiting for sync")

    def check_presync(self, imp, importer_id, params):
        repo_id = self.repo["id"]
        self.assertEqual(imp["config"], params)
        self.assertEqual(imp["repo_id"], repo_id)
        self.assertEqual(imp["id"], importer_id)
        self.assertEqual(imp["importer_type_id"], importer_id)
        self.assertFalse(imp["sync_in_progress"])
        self.assertIsNone(imp["last_sync"])

    def check_postsync(self):
        imp = self._get_importer()
        self.assertFalse(imp["sync_in_progress"])
        self.assertIsNotNone(imp["last_sync"])

    def test_simple_tree_sync(self):
        importer_id = 'simple_tree'
        params = example_trees.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertIsNone(self._sync_repo())
        self._wait_for_sync()
        self.check_postsync()
        self.check_tree_layout(self.local_path)


if __name__ == '__main__':
    unittest.main()
