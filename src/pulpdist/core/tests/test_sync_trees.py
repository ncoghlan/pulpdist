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
"""Basic test suite for sync transfer operations"""

import shutil
import os.path
from tempfile import NamedTemporaryFile
from cStringIO import StringIO
from datetime import datetime, timedelta

from .. import sync_trees, util
from . example_trees import TreeTestCase

_path = os.path.join

class BaseTestCase(TreeTestCase):
    def check_datetime(self, actual, reference, max_error_seconds=2):
        max_delta = timedelta(seconds=max_error_seconds)
        self.assertLessEqual(reference - actual, max_delta)

    def check_sync_details(self, details, expected_result, expected_stats):
        result, start_time, finish_time, stats = details
        self.assertEqual(result, expected_result)
        now = datetime.utcnow()
        self.check_datetime(start_time, now, 60)
        self.check_datetime(finish_time, now)
        self.check_stats(stats, expected_stats)

class TestSyncTree(BaseTestCase):

    def test_sync(self):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        stats = dict(self.EXPECTED_TREE_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_tree_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_tree_layout(local_path)

    def test_sync_versioned(self):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_VERSIONED_SYNC)
        task = sync_trees.SyncVersionedTree(params)
        stats = dict(self.EXPECTED_VERSIONED_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_versioned_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_versioned_layout(local_path)

    def test_sync_snapshot(self):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_SNAPSHOT_SYNC)
        details = self.setup_snapshot_layout(local_path)
        task = sync_trees.SyncSnapshotTree(params)
        stats = dict(self.EXPECTED_SNAPSHOT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_snapshot_layout(local_path, *details)
        # For an up-to-date tree, we transfer *nothing*
        for k in stats:
            stats[k] = 0
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_snapshot_layout(local_path, *details)

    def latest_link_info(self):
        link_name = u"latest-relevant"
        link_path = _path(self.local_path, link_name)
        return link_name, link_path

    def check_sync_latest_link(self):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_SNAPSHOT_SYNC)
        link_name, link_path = self.latest_link_info()
        params["latest_link_name"] = link_name
        __, expect_sync, __ = self.setup_snapshot_layout(local_path)
        task = sync_trees.SyncSnapshotTree(params)
        task.run_sync()
        # Symlink should exist and point to the last synced tree
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), expect_sync[-1])
        # Ensure the case where the link already exists is handled correctly
        task.run_sync()
        # Symlink should exist and point to the last synced tree
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), expect_sync[-1])

    def test_sync_latest_link(self):
        self.check_sync_latest_link()

    def test_sync_latest_link_existing_file(self):
        # BZ#807913 - make sure this works even if the name is already taken
        __, link_path = self.latest_link_info()
        with open(link_path, 'w') as f:
            pass
        self.check_sync_latest_link()

    def test_sync_latest_link_broken_symlink(self):
        # BZ#807913 - check broken symlinks are handled correctly
        __, link_path = self.latest_link_info()
        os.symlink("missing", link_path)
        self.check_sync_latest_link()

    def test_dir_protection(self):
        # We only test this with a simple sync
        # since versioned sync is merely a series
        # of simple syncs
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        protected_path = _path(local_path, "safe")
        protected_fname = _path(protected_path, "PROTECTED")
        os.makedirs(protected_path)
        with open(protected_fname, 'w') as f:
            pass
        unprotected_path = _path(local_path, "deleted")
        os.makedirs(unprotected_path)
        task.run_sync()
        self.check_tree_layout(local_path)
        self.assertExists(protected_path)
        self.assertExists(protected_fname)
        self.assertNotExists(unprotected_path)

    def test_file_consolidation(self):
        # We only test this with a simple sync
        # since the consolidation is handled by
        # the base class
        params = self.params
        params.update(self.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        extra_path = _path(rsyncd_path, "extra.txt")
        copied_path = _path(rsyncd_path, "copied.txt")
        with open(extra_path, 'w') as f:
            f.write("Hello world!")
        shutil.copy2(extra_path, copied_path)
        self.assertFalse(os.path.samefile(extra_path, copied_path))
        task.run_sync()
        local_path = self.local_path
        extra_path = _path(local_path, "extra.txt")
        copied_path = _path(local_path, "copied.txt")
        self.assertTrue(os.path.samefile(extra_path, copied_path))

    def log_simple_sync(self, log_dest):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params, log_dest)
        stats = self.EXPECTED_TREE_STATS
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_tree_layout(local_path)

    def check_version_logged(self, tree_type, log_data):
        version_info = "{0} {1}".format(tree_type, util.__version__)
        self.assertIn(version_info, log_data)

    def test_path_logging(self):
        with NamedTemporaryFile() as sync_log:
            self.log_simple_sync(sync_log.name)
            log_data = sync_log.read()
        self.check_version_logged("SyncTree", log_data)
        self.check_log_output(log_data,
                              "SYNC_COMPLETED",
                              self.EXPECTED_TREE_STATS)

    def test_stream_logging(self):
        stream = StringIO()
        self.log_simple_sync(stream)
        log_data = stream.getvalue()
        self.check_version_logged("SyncTree", log_data)
        self.check_log_output(log_data,
                              "SYNC_COMPLETED",
                              self.EXPECTED_TREE_STATS)

    def _remove_remote_trees(self, stats):
        source_dir = self.rsyncd.data_dir
        subtrees = "relevant-1 relevant-3".split()
        for tree in subtrees:
            shutil.rmtree(_path(source_dir, "versioned", tree))
        stats.update(self.EXPECTED_REPEAT_STATS)
        num_trees = len(subtrees)
        for k, v in stats.iteritems():
            if v:
                stats[k] = v - self.EXPECTED_TREE_STATS[k] * num_trees
        return subtrees

    def _protect_local_trees(self, trees):
        local_path = self.local_path
        for tree in trees:
            protected = _path(local_path, tree, "PROTECTED")
            with open(protected, 'w'):
                pass

    def _unprotect_local_trees(self, trees):
        local_path = self.local_path
        for tree in trees:
            protected = _path(local_path, tree, "PROTECTED")
            os.unlink(protected)

    def test_delete_old_dirs(self):
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_VERSIONED_SYNC)
        task = sync_trees.SyncVersionedTree(params)
        stats = dict(self.EXPECTED_VERSIONED_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_versioned_layout(local_path)
        subtrees = self._remove_remote_trees(stats)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_versioned_layout(local_path)
        params["delete_old_dirs"] = True
        self._protect_local_trees(subtrees)
        task = sync_trees.SyncVersionedTree(params)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_versioned_layout(local_path)
        self._unprotect_local_trees(subtrees)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_versioned_layout(local_path, ["relevant-2", "relevant-4"])

    def test_latest_link_preservation(self):
        # Ensure BZ#799211 has been addressed
        local_path = self.local_path
        params = self.params
        params.update(self.CONFIG_SNAPSHOT_SYNC)
        link_name = u"latest-relevant"
        link_path = _path(local_path, link_name)
        params["latest_link_name"] = link_name
        params["delete_old_dirs"] = True
        details = self.setup_snapshot_layout(local_path)
        latest_dir = details[1][-1]
        task = sync_trees.SyncSnapshotTree(params)
        result, __, __, __ = task.run_sync()
        self.assertEqual(result, "SYNC_COMPLETED")
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), latest_dir)
        self.check_snapshot_layout(local_path, *details)
        # Now we remove the relevant remote trees
        remote_dir = os.path.join(self.rsyncd.data_dir, "snapshot")
        shutil.rmtree(remote_dir)
        # And resync
        result, __, __, __ = task.run_sync()
        self.assertEqual(result, "SYNC_FAILED")
        # On an error, everything is preserved
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), latest_dir)
        self.check_snapshot_layout(local_path, *details)
        # Now set up a valid listing, but nothing to transfer
        os.makedirs(os.path.join(remote_dir, "relevant-new"))
        # And resync
        result, __, __, __ = task.run_sync()
        self.assertEqual(result, "SYNC_COMPLETED")
        # Now just the latest dir should be preserved
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), latest_dir)
        self.check_snapshot_layout(local_path, expected_paths=[latest_dir])


class TestSyncTreeDisabled(BaseTestCase):
    EXPECTED_NULL_STATS = sync_trees._null_sync_stats._asdict()

    def check_sync_details(self, details):
        local_path = self.local_path
        result, start_time, finish_time, stats = details
        self.assertEqual(result, "SYNC_DISABLED")
        now = datetime.utcnow()
        self.check_datetime(start_time, now)
        self.check_datetime(finish_time, now)
        self.check_stats(stats, self.EXPECTED_NULL_STATS)
        self.assertEqual(os.listdir(local_path), [])

    def check_disabled_sync(self, sync_type, sync_config):
        params = self.params
        params.update(sync_config)
        # Check with enabled set to False
        params["enabled"] = False
        task = sync_type(params)
        self.check_sync_details(task.run_sync())
        # Check with enabled not provided at all
        del params["enabled"]
        task = sync_type(params)
        self.check_sync_details(task.run_sync())

    def test_disabled_sync(self):
        self.check_disabled_sync(sync_trees.SyncTree,
                                 self.CONFIG_TREE_SYNC)

    def test_disabled_sync_versioned(self):
        self.check_disabled_sync(sync_trees.SyncVersionedTree,
                                 self.CONFIG_VERSIONED_SYNC)

    def test_disabled_sync_snapshot(self):
        self.check_disabled_sync(sync_trees.SyncSnapshotTree,
                                 self.CONFIG_SNAPSHOT_SYNC)

class TestSyncTreeDryRun(BaseTestCase):

    EXPECTED_DRY_RUN_STATS = dict(
        literal_bytes = 0,
        matched_bytes = 0,
    )

    def check_sync_details(self, details, expected_stats, expected_listdir):
        local_path = self.local_path
        result, start_time, finish_time, stats = details
        self.assertEqual(result, "SYNC_COMPLETED_DRY_RUN")
        now = datetime.utcnow()
        self.check_datetime(start_time, now, 60)
        self.check_datetime(finish_time, now)
        self.check_stats(stats, expected_stats)
        self.assertEqual(set(os.listdir(local_path)), set(expected_listdir))

    def check_dry_run_sync(self, sync_type, sync_config,
                                 expected_stats, expected_listdir=[]):
        params = self.params
        params.update(sync_config)
        params["dry_run_only"] = True
        task = sync_type(params)
        expected_stats.update(self.EXPECTED_DRY_RUN_STATS)
        self.check_sync_details(task.run_sync(),
                                expected_stats, expected_listdir)

    def test_dry_run_sync(self):
        self.check_dry_run_sync(sync_trees.SyncTree,
                                self.CONFIG_TREE_SYNC,
                                dict(self.EXPECTED_TREE_STATS))

    def test_dry_run_sync_versioned(self):
        stats = dict(self.EXPECTED_VERSIONED_STATS)
        stats["transferred_bytes"] *= self.NUM_TREES_VERSIONED
        stats["transferred_file_count"] *= self.NUM_TREES_VERSIONED
        self.check_dry_run_sync(sync_trees.SyncVersionedTree,
                                self.CONFIG_VERSIONED_SYNC,
                                stats)

    def test_dry_run_sync_snapshot(self):
        local_path = self.local_path
        existing_dir, __, __ = self.setup_snapshot_layout(local_path)
        stats = dict(self.EXPECTED_SNAPSHOT_STATS)
        stats["transferred_bytes"] *= self.NUM_TREES_SNAPSHOT
        stats["transferred_file_count"] *= self.NUM_TREES_SNAPSHOT
        self.check_dry_run_sync(sync_trees.SyncSnapshotTree,
                                self.CONFIG_SNAPSHOT_SYNC,
                                stats,
                                [os.path.basename(existing_dir)])


class TestLinkValidation(TreeTestCase):
    CONFIG_TREE_SYNC = dict(
        tree_name = u"Link Sanity Check",
        remote_server = u"localhost",
        remote_path = u"/test_data/",
        enabled = True,
    )

    CONFIG_TREE_VERSIONED = dict(
        tree_name = u"Versioned Link Check",
        remote_server = u"localhost",
        remote_path = u"/test_data/",
        enabled = True,
    )

    NUM_LINKS = 6

    def dirnames(self):
        return [u"dir" + str(i) for i in xrange(1, self.NUM_LINKS + 1)]

    def linknames(self):
        return [u"link" + str(i) for i in xrange(1, self.NUM_LINKS + 1)]

    def misc_links(self):
        return (u"link_etc link_missing link_file "
                 "link_loop_A link_loop_B").split()

    def make_layout(self, data_dir):
        os.mkdir(data_dir)
        for dirname, linkname in zip(self.dirnames(), self.linknames()):
            dirpath = _path(data_dir, dirname)
            os.mkdir(dirpath)
            with open(_path(dirpath, u"dummy.txt"), "w"):
                pass
            os.symlink(dirname, _path(data_dir, linkname))
        os.symlink(u"/etc", _path(data_dir, u"link_etc"))
        os.symlink(u"../test_data", _path(data_dir, u"link_missing"))
        os.symlink(u"dir1/dummy.txt", _path(data_dir, u"link_file"))
        os.symlink(u"link_loop_A", _path(data_dir, u"link_loop_B"))
        os.symlink(u"link_loop_B", _path(data_dir, u"link_loop_A"))

    def check_layout(self, dirnames=None, linknames=None,
                           extra_dirs=(), extra_links=None, extra_files=()):
        local_path = self.local_path
        if dirnames is None:
            dirnames = self.dirnames()
        if linknames is None:
            linknames = self.linknames()
        expected = dirnames + linknames
        if extra_links is None:
            extra_links = ["link_etc"]
        expected.extend(extra_links)
        expected.extend(extra_dirs)
        expected.extend(extra_files)
        expected.sort()
        self.assertEqual(sorted(os.listdir(local_path)), expected)
        for dirname, linkname in zip(dirnames, linknames):
            # Check the directory details
            dirpath = _path(local_path, dirname)
            self.assertTrue(os.path.isdir(dirpath), dirpath)
            self.assertFalse(os.path.islink(dirpath), dirpath)
            # Check the link details
            linkpath = _path(local_path, linkname)
            self.assertTrue(os.path.isdir(linkpath), linkpath)
            self.assertTrue(os.path.islink(linkpath), linkpath)
            self.assertEqual(os.readlink(linkpath), dirname)
        for name in extra_links:
            path = _path(local_path, name)
            self.assertTrue(os.path.islink(path), path)
        for name in extra_dirs:
            path = _path(local_path, name)
            self.assertFalse(os.path.islink(path), path)
            self.assertTrue(os.path.isdir(path), path)
        for name in extra_files:
            path = _path(local_path, name)
            self.assertFalse(os.path.islink(path), path)
            self.assertFalse(os.path.isdir(path), path)

    def test_tree_sync(self):
        # Sanity check that the tree is being created and served correctly
        params = self.params
        params.update(self.CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        task.run_sync()
        self.check_layout(extra_links=self.misc_links())

    def test_tree_versioned(self):
        params = self.params
        params.update(self.CONFIG_TREE_VERSIONED)
        task = sync_trees.SyncVersionedTree(params)
        task.run_sync()
        self.check_layout()

    def test_tree_fixes(self):
        params = self.params
        params.update(self.CONFIG_TREE_VERSIONED)
        local_path = self.local_path
        dirnames = self.dirnames()
        linknames = self.linknames()
        extra_links = [u"link_etc"]
        extra_dirs = []
        extra_files = []
        # Check a local directory will be replaced with a link and vice-versa
        os.mkdir(_path(local_path, u"link1"))
        os.symlink(u"link1", _path(local_path, u"dir1"))
        # Check that an existing link will be overwritten
        os.symlink(u"elsewhere", _path(local_path, u"link2"))
        # An existing link to the right place will be left alone
        os.symlink(u"dir3", _path(local_path, u"link3"))
        # Ordinary files are converted to links and directories
        with open(_path(local_path, u"dir4"), "w"):
            pass
        with open(_path(local_path, u"link4"), "w"):
            pass
        # Protected directories are left alone
        protected_path = _path(local_path, u"link5")
        os.mkdir(protected_path)
        with open(_path(protected_path, "PROTECTED"), "w"):
            pass
        linknames.remove(u"link5")
        dirnames.remove(u"dir5")
        extra_dirs.extend(u"link5 dir5".split())
        # Existing symlinks that loop back to the upstream name are left alone
        # Exclude this dir from the sync so the link remains in place
        params["exclude_from_listing"] = [u"dir6"]
        os.mkdir(_path(local_path, u"link6"))
        os.symlink(u"link6", _path(local_path, u"dir6"))
        dirnames.remove(u"dir6")
        linknames.remove(u"link6")
        dirnames.append(u"link6")
        linknames.append(u"dir6")
        # Finished setting up the local path to be fixed, run it!
        stream = StringIO()
        task = sync_trees.SyncVersionedTree(params, stream)
        task.run_sync()
        # Now check all the little scenarios have the expected results
        log_output = stream.getvalue()
        self.assertIn("replacing with directory", log_output)
        self.check_layout(dirnames, linknames, extra_dirs, extra_links, extra_files)
        start_symlink_checks = log_output.index("validity of upstream symlinks")
        start_hardlink = log_output.index("Consolidating downloaded data")
        symlink_data = log_output[start_symlink_checks:start_hardlink]
        self.assertIn("Checking symlink", symlink_data)
        self.assertIn("Removing old directory", symlink_data)
        self.assertIn("already exists", symlink_data)
        self.assertIn("Unlinking old file", symlink_data)
        self.assertIn("Skipping existing directory", symlink_data)
        self.assertIn("links back to", symlink_data)
        self.assertIn("is not a directory, ignoring symlink", symlink_data)
        self.assertIn("does not exist, ignoring symlink", symlink_data)


if __name__ == '__main__':
    import unittest
    unittest.main()
