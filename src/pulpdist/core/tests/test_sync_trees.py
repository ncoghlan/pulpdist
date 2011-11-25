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

from .. import sync_trees
from . example_trees import (expected_versioned_trees, TreeTestCase,
                             CONFIG_TREE_SYNC, CONFIG_VERSIONED_SYNC,
                             CONFIG_SNAPSHOT_SYNC)

class TestSyncTree(TreeTestCase):
    def test_sync(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        task.run_sync()
        self.check_tree_layout(local_path)

    def test_sync_versioned(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_VERSIONED_SYNC)
        task = sync_trees.SyncVersionedTree(params)
        task.run_sync()
        for tree in expected_versioned_trees:
            tree_path = os.path.join(local_path, tree)
            self.check_tree_layout(tree_path)

    def test_sync_snapshot(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_SNAPSHOT_SYNC)
        # Set up one local tree as already FINISHED
        skip_finished = expected_versioned_trees[0]
        finished_path = os.path.join(local_path, skip_finished)
        os.makedirs(finished_path)
        self.mark_trees_finished(local_path, [skip_finished])
        # Set up all bar one remote tree as FINISHED
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        expect_sync = expected_versioned_trees[1:-1]
        self.mark_trees_finished(rsyncd_path, [skip_finished] + expect_sync)
        # The last tree we expect to be skipped
        skip_not_ready = expected_versioned_trees[-1]
        not_ready_path = os.path.join(local_path, skip_not_ready)
        # Run the sync task
        task = sync_trees.SyncSnapshotTree(params)
        task.run_sync()
        # The tree locally marked as complete should not get updated
        self.assertExists(finished_path)
        self.assertEqual(os.listdir(finished_path), ["STATUS"])
        # The tree not remotely marked as complete should not get updated
        self.assertNotExists(not_ready_path)
        # The other trees should all get synchronised
        previous_tree_path = None
        for tree in expect_sync:
            tree_path = os.path.join(local_path, tree)
            self.check_tree_layout(tree_path)
            if previous_tree_path is not None:
                self.check_tree_cross_links(tree_path, previous_tree_path)
            previous_tree_path = tree_path
            status_path = os.path.join(tree_path, "STATUS")
            self.assertExists(status_path)
            with open(status_path) as f:
                self.assertEqual(f.read().strip(), "FINISHED")

    def test_sync_latest_link(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_SNAPSHOT_SYNC)
        link_name = u"latest-relevant"
        link_path = os.path.join(local_path, link_name)
        params["latest_link_name"] = link_name
        # Set up all the remote trees as FINISHED
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        self.mark_trees_finished(rsyncd_path, expected_versioned_trees)
        task = sync_trees.SyncSnapshotTree(params)
        task.run_sync()
        # Symlink should exist and point to the last tree
        self.assertTrue(os.path.islink(link_path))
        expected_target = expected_versioned_trees[-1]
        self.assertEqual(os.readlink(link_path), expected_target)


    def test_dir_protection(self):
        # We only test this with a simple sync
        # since versioned sync is merely a series
        # of simple syncs
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        protected_path = os.path.join(local_path, "safe")
        protected_fname = os.path.join(protected_path, "PROTECTED")
        os.makedirs(protected_path)
        with open(protected_fname, 'w') as f:
            pass
        unprotected_path = os.path.join(local_path, "deleted")
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
        params.update(CONFIG_TREE_SYNC)
        task = sync_trees.SyncTree(params)
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        extra_path = os.path.join(rsyncd_path, "extra.txt")
        copied_path = os.path.join(rsyncd_path, "copied.txt")
        with open(extra_path, 'w') as f:
            f.write("Hello world!")
        shutil.copy2(extra_path, copied_path)
        self.assertFalse(os.path.samefile(extra_path, copied_path))
        task.run_sync()
        local_path = self.local_path
        extra_path = os.path.join(local_path, "extra.txt")
        copied_path = os.path.join(local_path, "copied.txt")
        self.assertTrue(os.path.samefile(extra_path, copied_path))


    # TODO: Verify copying of other symlinks
    # TODO: Delete old versioned directories


if __name__ == '__main__':
    import unittest
    unittest.main()
