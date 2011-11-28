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
from . example_trees import (CONFIG_TREE_SYNC, CONFIG_VERSIONED_SYNC,
                             CONFIG_SNAPSHOT_SYNC,
                             TreeTestCase)

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
        self.check_versioned_layout(local_path)

    def test_sync_snapshot(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_SNAPSHOT_SYNC)
        details = self.setup_snapshot_layout(local_path)
        task = sync_trees.SyncSnapshotTree(params)
        task.run_sync()
        self.check_snapshot_layout(local_path, *details)

    def test_sync_latest_link(self):
        local_path = self.local_path
        params = self.params
        params.update(CONFIG_SNAPSHOT_SYNC)
        link_name = u"latest-relevant"
        link_path = os.path.join(local_path, link_name)
        params["latest_link_name"] = link_name
        __, expect_sync, __ = self.setup_snapshot_layout(local_path)
        task = sync_trees.SyncSnapshotTree(params)
        task.run_sync()
        # Symlink should exist and point to the last sync'ed tree
        self.assertTrue(os.path.islink(link_path))
        self.assertEqual(os.readlink(link_path), expect_sync[-1])

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
