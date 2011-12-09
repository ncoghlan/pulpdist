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
import socket
import time
import os
from datetime import datetime, timedelta

from parse import parse as parse_str

from ...core import pulpapi, sync_trees
from ...core.tests import example_trees
from ...core.tests.compat import unittest

# Required setup on local machine to run plugin tests
#
# - Pulp instance running on default port (i.e. 80)
# - default admin/admin account still in place
# - OAuth enabled with keys as seen below
# - "pulp-admin auth login localhost --username admin --password admin"

# TODO: Parts of the below should become pulpdist.core.tests.test_pulpapi
#       (Although it's handy that the core tests don't need the server...)


IMPORTERS = [u"simple_tree", u"versioned_tree", u"snapshot_tree",
             u"delta_tree", u"snapshot_delta"]

def _naive_utc(dt):
    if dt.utcoffset() is None:
        return dt # already naive
    return (dt - dt.utcoffset()).replace(tzinfo=None)

def parse_iso_datetime(raw):
    dt = parse_str("{:ti}", raw).fixed[0]
    return _naive_utc(dt)

class PulpTestCase(unittest.TestCase):
    REPO_ID = u"test_repo"

    def setUp(self):
        self.server = self._local_test_server()

    def _local_test_server(self):
        localhost = socket.gethostname()
        oauth_key = "example-oauth-key"
        oauth_secret = "example-oauth-secret"
        return pulpapi.PulpServer(localhost, oauth_key, oauth_secret)

    def _local_test_repo(self):
        try:
            self.server.delete_repo(self.REPO_ID)
        except pulpapi.ServerRequestError:
            pass
        else:
            raise RuntimeError("Previous test run didn't destroy test repo!")
        return self.server.create_repo(self.REPO_ID)

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


class TestServerAccess(PulpTestCase):
    # Test basic access to the local Pulp server
    # including whether or not the pulpdist plugins
    # are installed correctly

    def test_importers_loaded(self):
       importers = self.server.get_generic_importers()
       expected = set(IMPORTERS)
       for importer in importers:
           expected.remove(importer[u"id"])
       if expected:
           self.fail("Missing expected importers: {0}".format(list(expected)))

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

class TestBasicAuthServerAccess(BasicAuthMixin, TestServerAccess): pass
class TestLocalCertServerAccess(LocalCertMixin, TestServerAccess): pass

class TestConfiguration(PulpTestCase):
    # Test configuration of importers without
    # actually trying to sync anything

    def setUp(self):
        super(TestConfiguration, self).setUp()
        self.repo = self._local_test_repo()

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
        params = example_trees.TreeTestCase.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_versioned_tree(self):
        importer_id = u"versioned_tree"
        params = example_trees.TreeTestCase.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

    def test_snapshot_tree(self):
        importer_id = u"snapshot_tree"
        params = example_trees.TreeTestCase.CONFIG_SNAPSHOT_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_importer(imp, importer_id, params)

class TestBasicAuthConfiguration(BasicAuthMixin, TestConfiguration): pass
class TestLocalCertConfiguration(LocalCertMixin, TestConfiguration): pass

class TestLocalSync(example_trees.TreeTestCase, PulpTestCase):
    # Actually test synchronisation

    def setUp(self):
        super(TestLocalSync, self).setUp()
        self.server = self._local_test_server()
        self.repo = self._local_test_repo()
        # Ensure Pulp server can write to our data dir
        os.chmod(self.local_path, 0o777)

    def tearDown(self):
        self.server.delete_repo(self.repo[u"id"])

    def _add_importer(self, importer_id, params):
        params.update(self.params)
        repo_id = self.repo[u"id"]
        return self.server.add_importer(repo_id, importer_id, params)

    def _get_repo(self):
        return self.server.get_repo(self.repo[u"id"])

    def _get_importer(self):
        return self.server.get_importer(self.repo[u"id"])

    def _sync_repo(self):
        return self.server.sync_repo(self.repo[u"id"])

    def _get_sync_history(self):
        return self.server.get_sync_history(self.repo[u"id"])

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
        self.assertIsNone(imp[u"scratchpad"])

    def check_iso_datetime(self, iso_str,
                           reference_time=None,
                           max_error_seconds=2):
        self.assertIsNotNone(iso_str)
        dt = parse_iso_datetime(iso_str)
        self.assertIsInstance(dt, datetime)
        if reference_time is not None:
            max_delta = timedelta(seconds=max_error_seconds)
            self.assertLessEqual(reference_time - dt, max_delta)

    def check_stats(self, actual, expected):
        for field, expected_value in expected.iteritems():
            actual_value = actual[field]
            msg = "sync stats field {0!r}".format(field)
            self.assertEqual(actual_value, expected_value, msg)

    def check_postsync(self, expected_result, expected_stats):
        imp = self._get_importer()
        self.assertFalse(imp[u"sync_in_progress"])
        sync_time = imp[u"last_sync"]
        now = datetime.utcnow()
        self.check_iso_datetime(sync_time, now)
        history = self._get_sync_history()
        self.assertGreaterEqual(len(history), 1)
        sync_meta = history[0]
        # TODO: Report and check sync status properly
        # print(sync_meta["summary"]["result"])
        # Check top level sync history
        self.assertEqual(sync_meta[u"result"], u"success")
        self.assertIsNotNone(sync_meta[u"started"])
        self.assertIsNotNone(sync_meta[u"added_count"])
        self.assertIsNotNone(sync_meta[u"removed_count"])
        self.check_iso_datetime(sync_meta[u"completed"], now)
        # Check summary
        summary = sync_meta[u"summary"]
        self.check_iso_datetime(summary[u"start_time"], now, 60)
        self.check_iso_datetime(summary[u"finish_time"], now)
        stats = summary[u"stats"]
        self.assertIsInstance(stats, dict)
        if expected_stats is not None:
            self.check_stats(stats, expected_stats)
        # Check details
        details = sync_meta[u"details"]
        self.assertIsInstance(details[u"sync_log"], unicode)

    def test_simple_tree_sync(self):
        importer_id = u"simple_tree"
        params = self.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        stats = self.EXPECTED_TREE_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_tree_layout(self.local_path)

    def test_versioned_tree_sync(self):
        importer_id = u"versioned_tree"
        params = self.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        stats = self.EXPECTED_VERSIONED_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_versioned_layout(self.local_path)

    def test_snapshot_tree_sync(self):
        importer_id = u"snapshot_tree"
        params = self.CONFIG_SNAPSHOT_SYNC.copy()
        details = self.setup_snapshot_layout(self.local_path)
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertTrue(self._sync_repo())
        self._wait_for_sync()
        stats = self.EXPECTED_SNAPSHOT_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_snapshot_layout(self.local_path, *details)

class TestBasicAuthLocalSync(BasicAuthMixin, TestLocalSync): pass
class TestLocalCertLocalSync(LocalCertMixin, TestLocalSync): pass

if __name__ == '__main__':
    unittest.main()
