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
import os
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from dateutil.tz import tzutc

from ...core import pulpapi, sync_trees
from ...core.tests import example_trees

IMPORTERS = [u"simple_tree", u"versioned_tree", u"snapshot_tree", u"delta_tree", u"snapshot_delta"]

def _local_test_server():
    localhost = socket.gethostname()
    oauth_key = "example-oauth-key"
    oauth_secret = "example-oauth-secret"
    return pulpapi.PulpServer(localhost, oauth_key, oauth_secret)

def _naive_utc(dt):
    return dt.astimezone(tzutc()).replace(tzinfo=None)

class PulpTestCase(unittest.TestCase):

    def setUp(self):
        self.server = _local_test_server()

class TestServerAccess(PulpTestCase):
    # Test basic access to the local Pulp server
    # including whether or not the pulpdist plugins
    # are installed correctly
    REPO_ID = u"test_repo"

    def test_importers_loaded(self):
       importers = self.server.get_generic_importers()
       expected = set(IMPORTERS)
       for importer in importers:
           expected.remove(importer[u"id"])
       if expected:
           self.fail("Missing expected importers: {}".format(list(expected)))

    def test_missing_repo(self):
        with self.assertRaises(pulpapi.ServerRequestError) as details:
            self.server.get_repo(self.REPO_ID)
        exc = details.exception
        self.assertEqual(exc.args[0], 404)

    def test_create_and_delete_repo(self):
        repo_id = self.REPO_ID
        repo_name = u"Test Repo"
        description = u"This is a test repo!"
        repo = self.server.create_repo(repo_id, repo_name, description)
        self.assertTrue(self.server.delete_repo(repo_id))
        self.assertEqual(repo[u"id"], repo_id)
        self.assertEqual(repo[u"display_name"], repo_name)
        self.assertEqual(repo[u"description"], description)
        # Ensure it is really gone
        with self.assertRaises(pulpapi.ServerRequestError) as details:
            self.server.get_repo(self.REPO_ID)
        exc = details.exception
        self.assertEqual(exc.args[0], 404)

class TestConfiguration(PulpTestCase):
    # Test configuration of importers without
    # actually trying to sync anything
    REPO_ID = u"test_repo"

    def setUp(self):
        super(TestConfiguration, self).setUp()
        self.repo = self.server.create_repo(self.REPO_ID)

    def tearDown(self):
        self.server.delete_repo(self.repo[u"id"])

    def _add_importer(self, importer_id, params):
        params[u"local_path"] = u"test_path"
        repo_id = self.repo[u"id"]
        return self.server.add_importer(repo_id, importer_id, params)

    def check_importer(self, imp, importer_id, params):
        repo_id = self.repo[u"id"]
        self.assertEqual(imp[u"config"], params)
        self.assertEqual(imp[u"repo_id"], repo_id)
        self.assertEqual(imp[u"id"], importer_id)
        self.assertEqual(imp[u"importer_type_id"], importer_id)
        self.assertFalse(imp[u"sync_in_progress"])
        self.assertIsNone(imp[u"last_sync"])
        self.check_get_importer(repo_id, imp)

    def check_get_importer(self, repo_id, imp):
        importers = self.server.get_importers(repo_id)
        self.assertEqual(len(importers), 1)
        self.assertEqual(importers[0], imp)

    def test_no_importer(self):
        repo_id = self.repo[u"id"]
        self.assertEqual(self.server.get_importers(repo_id), [])

    def test_simple_tree(self):
        importer_id = u"simple_tree"
        params = example_trees.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_versioned_tree(self):
        importer_id = u"versioned_tree"
        params = example_trees.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_snapshot_tree(self):
        importer_id = u"snapshot_tree"
        params = example_trees.CONFIG_SNAPSHOT_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

class TestLocalSync(example_trees.TreeTestCase):
    # Actually test synchronisation
    REPO_ID = u"test_repo"

    def setUp(self):
        super(TestLocalSync, self).setUp()
        self.server = _local_test_server()
        self.repo = self.server.create_repo(self.REPO_ID)
        # Ensure Pulp server can write to our data dir
        os.chmod(self.local_path, 0o777)
        # Use the server's default logging option
        self.params["log_path"] = None

    def tearDown(self):
        self.server.delete_repo(self.repo[u"id"])

    def _add_importer(self, importer_id, params):
        params.update(self.params)
        repo_id = self.repo[u"id"]
        return self.server.add_importer(repo_id, importer_id, params)

    def _get_importer(self):
        return self.server.get_importer(self.repo[u"id"])

    def _sync_repo(self):
        return self.server.sync_repo(self.repo[u"id"])

    def _wait_for_sync(self):
        deadline = time.time() + 10
        sync_started = False
        while time.time() < deadline:
            imp = self._get_importer()
            if imp[u"last_sync"] is not None:
                break
            if sync_started:
                self.assertTrue(imp[u"sync_in_progress"])
            else:
                sync_started = imp[u"sync_in_progress"]
            time.sleep(0.1)
        else:
            self.fail("Timed out waiting for sync")

    def check_presync(self, imp, importer_id, params):
        repo_id = self.repo[u"id"]
        self.assertEqual(imp[u"config"], params)
        self.assertEqual(imp[u"repo_id"], repo_id)
        self.assertEqual(imp[u"id"], importer_id)
        self.assertEqual(imp[u"importer_type_id"], importer_id)
        self.assertFalse(imp[u"sync_in_progress"])
        self.assertIsNone(imp[u"last_sync"])

    def check_postsync(self):
        imp = self._get_importer()
        self.assertFalse(imp[u"sync_in_progress"])
        last_sync = imp[u"last_sync"]
        self.assertIsNotNone(last_sync)
        sync_time = _naive_utc(parse_date(last_sync))
        now = datetime.utcnow()
        self.assertLess(now - sync_time, timedelta(seconds=2))

    def test_simple_tree_sync(self):
        importer_id = u"simple_tree"
        params = example_trees.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        self.check_postsync()
        self.check_tree_layout(self.local_path)

    def test_versioned_tree_sync(self):
        importer_id = u"versioned_tree"
        params = example_trees.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        self.check_postsync()
        self.check_versioned_layout(self.local_path)

    def test_snapshot_tree_sync(self):
        importer_id = u"snapshot_tree"
        params = example_trees.CONFIG_SNAPSHOT_SYNC.copy()
        details = self.setup_snapshot_layout(self.local_path, params["remote_path"])
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        self.check_postsync()
        self.check_snapshot_layout(self.local_path, *details)


if __name__ == '__main__':
    unittest.main()
