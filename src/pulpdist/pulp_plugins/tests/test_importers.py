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

from ...core import util
from ...core.tests import example_trees
from ...core.tests.pulpapi_util import (PulpTestCase,
                                        BasicAuthMixin,
                                        LocalCertMixin)
from ...core.tests.compat import unittest

IMPORTERS = [u"simple_tree", u"versioned_tree", u"snapshot_tree",
             u"delta_tree", u"snapshot_delta"]

def _calc_sync_log_dir():
    SYNC_LOG_RELPATH = "var/www/pub/pulpdist_sync_logs"
    # We're in src/pulpdist/pulp_plugins/tests/test_importers in Git
    # so need to go up 4 dirs to find the common path to the log files
    this_dir = os.path.realpath(os.path.dirname(__file__))
    base_dir = os.path.abspath(this_dir + "/../../../..")
    return os.path.abspath(
               os.path.normpath(
                   os.path.join(base_dir, SYNC_LOG_RELPATH)))

SYNC_LOG_DIR = _calc_sync_log_dir()

def _naive_utc(dt):
    if dt.utcoffset() is None:
        return dt # already naive
    return (dt - dt.utcoffset()).replace(tzinfo=None)

def parse_iso_datetime(raw):
    dt = parse_str("{:ti}", raw).fixed[0]
    return _naive_utc(dt)

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
        with self.assertServerRequestError() as details:
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
        with self.assertServerRequestError() as details:
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
        self.repo = self.local_test_repo()

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

    def _get_sync_log_paths(self):
        log_path = os.path.join(SYNC_LOG_DIR, self.REPO_ID + ".log")
        return log_path, log_path + ".prev", log_path + ".bak"


    def _remove_logs(self):
        for log_path in self._get_sync_log_paths():
            try:
                os.unlink(log_path)
            except OSError:
                continue

    def setUp(self):
        super(TestLocalSync, self).setUp()
        # Due to the multiple inheritance arrangement, the super() call
        # doesn't  automatically set up our connection to the Pulp server
        self.server = self.local_test_server()
        self.repo = self.local_test_repo()
        # Ensure Pulp server can write to our data dir
        os.chmod(self.local_path, 0o777)
        self._remove_logs()

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

    def _wait_for_sync(self, previous_sync=None):
        deadline = time.time() + 10
        sync_started = False
        while time.time() < deadline:
            imp = self._get_importer()
            last_sync = imp[u"last_sync"]
            if last_sync != previous_sync:
                return last_sync
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

    def check_log(self, log_path, expected_result, expected_stats):
        self.assertExists(log_path)
        with open(log_path) as sync_log:
            self.check_log_output(sync_log.read(),
                                  expected_result,
                                  expected_stats)

    def check_logs(self, expected_result, expected_stats,
                         previous_result=None, previous_stats=None):
        log_path, previous_path, backup_path  = self._get_sync_log_paths()
        # Check current log
        self.check_log(log_path, expected_result, expected_stats)
        # Check previous log is always backed up
        if previous_result is not None:
            self.check_log(previous_path, previous_result, previous_stats)
        else:
            self.assertNotExists(previous_path)
        # Check successful log is backed up
        if "SYNC_COMPLETED" in (expected_result, previous_result):
            if expected_result == "SYNC_COMPLETED":
                backup_result = expected_result
                backup_stats = expected_stats
            else:
                backup_result = previous_result
                backup_stats = previous_stats
            self.check_log(backup_path, backup_result, backup_stats)
        else:
            self.assertNotExists(backup_path)

    def check_postsync_common(self):
        imp = self._get_importer()
        self.assertFalse(imp[u"sync_in_progress"])
        sync_time = imp[u"last_sync"]
        now = datetime.utcnow()
        self.check_iso_datetime(sync_time, now)
        history = self._get_sync_history()
        self.assertGreaterEqual(len(history), 1)
        return imp, now, history[0]

    def check_postsync(self, expected_result, expected_stats,
                             previous_result=None, previous_stats=None):
        imp, now, sync_meta = self.check_postsync_common()
        # TODO: Report and check Pulp level sync status properly
        #       Requires Pulp upgrade to get access to relevant plugin API
        # Check top level sync history
        self.assertEqual(sync_meta[u"result"], u"success")
        self.assertIsNotNone(sync_meta[u"started"])
        self.assertIsNotNone(sync_meta[u"added_count"])
        self.assertIsNotNone(sync_meta[u"removed_count"])
        self.check_iso_datetime(sync_meta[u"completed"], now)
        # Check summary
        summary = sync_meta[u"summary"]
        self.assertEqual(summary[u"result"], expected_result)
        self.check_iso_datetime(summary[u"start_time"], now, 60)
        self.check_iso_datetime(summary[u"finish_time"], now)
        stats = summary[u"stats"]
        self.assertIsInstance(stats, dict)
        if expected_stats is not None:
            self.check_stats(stats, expected_stats)
        # Check details
        details = sync_meta[u"details"]
        self.assertEqual(details[u"plugin_type"], imp[u"importer_type_id"])
        self.assertEqual(details[u"plugin_version"], util.__version__)
        # BZ#799203 - sync log is no longer saved in the sync history
        self.assertNotIn(u"sync_log", details)
        self.check_logs(expected_result, expected_stats,
                        previous_result, previous_stats)

    def check_sync_error(self, expected_error):
        imp, now, sync_meta = self.check_postsync_common()
        self.assertEqual(sync_meta[u"result"], u"error")
        self.assertIsNone(sync_meta[u"summary"])
        self.assertIsNone(sync_meta[u"details"])
        # Check the error is the expected one
        self.assertIn(expected_error, sync_meta[u"exception"])
        actual_error = sync_meta[u"error_message"]
        self.assertIn(expected_error, actual_error)
        # Check the exception was written out to the log file
        log_path, previous_path, backup_path  = self._get_sync_log_paths()
        with open(log_path) as sync_log:
            log_data = sync_log.read()
            self.assertIn("PLUGIN ERROR", log_data)
            self.assertIn("Traceback (most recent", log_data)
            self.assertIn(actual_error, log_data)

    def test_simple_tree_sync_partial(self):
        importer_id = u"simple_tree"
        params = self.CONFIG_TREE_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertEqual(self._sync_repo(), {})
        self._wait_for_sync()
        stats = self.EXPECTED_TREE_STATS
        # With the default settings, the rsync download in the
        # plugin encounters a non-fatal error that prompts it to
        # report that some files couldn't be downloaded. It's
        # wrong about that, but we can use it to check the
        # partial sync reporting.
        self.check_postsync("SYNC_PARTIAL", stats)
        self.check_tree_layout(self.local_path)

    def check_simple_tree_sync(self):
        # Factored out as a helper method so we can use in multiple places
        importer_id = u"simple_tree"
        params = self.CONFIG_TREE_SYNC.copy()
        # Work around for the odd behaviour described under
        # test_simple_tree_sync_partial
        local_path = os.path.join(self.params["local_path"], "simple_tree/")
        self.local_path = self.params["local_path"] = local_path
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertEqual(self._sync_repo(), {})
        last_sync = self._wait_for_sync()
        stats = self.EXPECTED_TREE_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_tree_layout(self.local_path)
        return last_sync, stats

    def test_simple_tree_sync(self):
        self.check_simple_tree_sync()

    def test_versioned_tree_sync(self):
        importer_id = u"versioned_tree"
        params = self.CONFIG_VERSIONED_SYNC.copy()
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertEqual(self._sync_repo(), {})
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
        self.assertEqual(self._sync_repo(), {})
        self._wait_for_sync()
        stats = self.EXPECTED_SNAPSHOT_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_snapshot_layout(self.local_path, *details)

    def test_latest_snapshot_tree_sync(self):
        importer_id = u"snapshot_tree"
        params = self.CONFIG_LATEST_SNAPSHOT_SYNC.copy()
        details = self.setup_latest_snapshot_layout(self.local_path)
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertEqual(self._sync_repo(), {})
        self._wait_for_sync()
        stats = self.EXPECTED_LATEST_SNAPSHOT_STATS
        self.check_postsync("SYNC_COMPLETED", stats)
        self.check_snapshot_layout(self.local_path, *details)

    def test_sync_log_backup(self):
        # First, we repeat test_simple_tree_sync to get a good backup
        last_sync, previous_stats = self.check_simple_tree_sync()
        # Then we rerun the sync without making any changes
        # Timestamp resolution is only 1 second, so we ensure it changes
        # Once we upgrade to a more recent Pulp version, we'll have the full
        # async tasking REST API available and this "wait for sync" dance
        # can be cleaned up significantly
        time.sleep(1.5) 
        self.assertEqual(self._sync_repo(), {})
        self._wait_for_sync(last_sync)
        stats = self.EXPECTED_TREE_STATS.copy()
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_postsync("SYNC_UP_TO_DATE", stats,
                            "SYNC_COMPLETED", previous_stats)
        self.check_tree_layout(self.local_path)

    def test_sync_failure(self):
        # Deliberately trigger an exception by preventing write access
        importer_id = u"simple_tree"
        params = self.CONFIG_TREE_SYNC.copy()
        parent_dir = self.params["local_path"]
        local_path = os.path.join(parent_dir, "simple_tree/")
        self.local_path = self.params["local_path"] = local_path
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        os.chmod(parent_dir, 0444)
        try:
            self.assertServerRequestError(self._sync_repo)
        finally:
            os.chmod(parent_dir, 0644)
        self.check_sync_error("Permission denied")

    def test_importer_update(self):
        last_sync, previous_stats = self.check_simple_tree_sync()
        # As with the backup log test, currently need to force a delay to
        # ensure the timestamp changes between runs :(
        time.sleep(1.5)
        # Tweak the settings to write to a new subdirectory
        importer_id = u"simple_tree"
        params = self.CONFIG_TREE_SYNC.copy()
        local_path = os.path.join(self.local_path, "different_dir/")
        self.local_path = self.params["local_path"] = local_path
        imp = self._add_importer(importer_id, params)
        self.check_presync(imp, importer_id, params)
        self.assertEqual(self._sync_repo(), {})
        last_sync = self._wait_for_sync()
        stats = self.EXPECTED_TREE_STATS
        self.check_postsync("SYNC_COMPLETED", stats,
                            "SYNC_COMPLETED", previous_stats)
        self.check_tree_layout(self.local_path)


class TestBasicAuthLocalSync(BasicAuthMixin, TestLocalSync): pass
class TestLocalCertLocalSync(LocalCertMixin, TestLocalSync): pass

if __name__ == '__main__':
    unittest.main()
