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

"""Tree definitions for use in testing"""

import shutil
import tempfile
import os.path

from .compat import unittest

from . import rsync_daemon
from .. import sync_trees

expected_files = [
    u"data.txt",
    u"data2.txt",
]

unexpected_files = [
    u"skip.txt",
]

test_files = expected_files + unexpected_files

expected_layout = [
    u"",
    u"subdir",
    u"subdir/subdir",
    u"subdir2",
]

unexpected_dirs = [
    u"subdir/irrelevant",
    u"subdir/subdir/irrelevant",
    u"subdir2/dull",
]

source_layout = expected_layout + unexpected_dirs

# For versioned trees, all 4 folders are always synced
_expected_versioned_trees = [u"relevant-{0}".format(i) for i in range(1, 5)]
# For snapshots, we mess with the STATUS files to be selective in syncing them
_skipped_snapshot_tree = _expected_versioned_trees[2]
_expected_snapshot_trees = _expected_versioned_trees[:]
del _expected_snapshot_trees[2]

source_trees = [
    u"simple",
    u"versioned/ignored",
    u"versioned/relevant-but-not-really",
    u"snapshot/ignored",
    u"snapshot/relevant-but-not-really",
]

source_trees.extend(os.path.join(u"versioned", tree) for tree in _expected_versioned_trees)
source_trees.extend(os.path.join(u"snapshot", tree) for tree in _expected_versioned_trees)

test_trees_finished = [os.path.join(u"snapshot", tree) for tree in _expected_snapshot_trees]

test_data_layout = [
    os.path.join(tree_dir, subdir)
        for tree_dir in source_trees
            for subdir in source_layout
]

def mark_trees_finished(base_dir, trees):
    for tree in trees:
        status_path = os.path.join(base_dir, tree, u"STATUS")
        with open(status_path, 'w') as f:
            f.write("FINISHED\n")


def make_layout(base_dir,
                dir_layout=test_data_layout,
                filenames=test_files,
                finished_trees=test_trees_finished):
    for data_dir in dir_layout:
        dpath = os.path.join(base_dir, data_dir)
        os.makedirs(dpath)
        for fname in filenames:
            fpath = os.path.join(dpath, fname)
            with open(fpath, 'w') as f:
                f.write("PulpDist test data!\n")
            # print("Created {0:!r})".format(fpath))
    # For better snapshot testing, only some trees are
    # flagged as being complete
    mark_trees_finished(base_dir, finished_trees)

def start_rsyncd(make_layout=make_layout):
    rsyncd = rsync_daemon.RsyncDaemon(make_layout)
    rsyncd.start()
    return rsyncd

class TreeTestCase(unittest.TestCase):
    TEST_DATA_LAYOUT = test_data_layout
    TEST_FILENAMES = test_files
    TEST_FINISHED_TREES = test_trees_finished

    def make_layout(self, base_dir):
        return make_layout(base_dir,
                           self.TEST_DATA_LAYOUT,
                           self.TEST_FILENAMES,
                           self.TEST_FINISHED_TREES)

    def start_rsyncd(self):
        return start_rsyncd(self.make_layout)

    CONFIG_TREE_SYNC = dict(
        tree_name = u"Simple Tree",
        remote_server = u"localhost",
        remote_path = u"/test_data/simple/",
        exclude_from_sync = u"*skip*".split(),
        sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
        enabled = True,
    )

    CONFIG_VERSIONED_SYNC = dict(
        tree_name = u"Versioned Tree",
        remote_server = u"localhost",
        remote_path = u"/test_data/versioned/",
        listing_pattern = u"relevant*",
        exclude_from_listing = u"relevant-but*".split(),
        exclude_from_sync = u"*skip*".split(),
        sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
        enabled = True,
    )

    CONFIG_SNAPSHOT_SYNC = dict(
        tree_name = u"Snapshot Tree",
        remote_server = u"localhost",
        remote_path = u"/test_data/snapshot/",
        listing_pattern = u"relevant*",
        exclude_from_listing = u"relevant-but*".split(),
        exclude_from_sync = u"*skip*".split(),
        sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
        enabled = True,
    )

    NUM_TREES_VERSIONED = 4
    NUM_TREES_SNAPSHOT = 2

    EXPECTED_TREE_STATS = dict(
        total_file_count = 12,
        total_bytes = 160,
    )
    EXPECTED_VERSIONED_STATS = dict(EXPECTED_TREE_STATS)
    EXPECTED_SNAPSHOT_STATS = dict(EXPECTED_TREE_STATS)
    for k in EXPECTED_TREE_STATS:
        EXPECTED_VERSIONED_STATS[k] *= NUM_TREES_VERSIONED
        EXPECTED_SNAPSHOT_STATS[k] *= NUM_TREES_SNAPSHOT
    del k

    _COMMON_STATS = dict(
        transferred_file_count = 8,
        transferred_bytes = 160,
        literal_bytes = 160,
        matched_bytes = 0,
    )

    EXPECTED_TREE_STATS.update(_COMMON_STATS)
    EXPECTED_VERSIONED_STATS.update(_COMMON_STATS)
    EXPECTED_SNAPSHOT_STATS.update(_COMMON_STATS)

    EXPECTED_REPEAT_STATS = dict(
        transferred_file_count = 0,
        transferred_bytes = 0,
        literal_bytes = 0,
        matched_bytes = 0,
    )

    def setUp(self):
        self.rsyncd = rsyncd = self.start_rsyncd()
        self.local_path = local_path = tempfile.mkdtemp().decode("utf-8")
        self.params = dict(rsync_port = rsyncd.port,
                           local_path = local_path+'/')

    def tearDown(self):
        self.rsyncd.close()
        shutil.rmtree(self.local_path)

    def assertExists(self, full_path):
        err = "{0} does not exist".format(full_path)
        # print ("Checking {0} exists".format(full_path))
        self.assertTrue(os.path.exists(full_path), err)

    def assertNotExists(self, full_path):
        err = "{0} exists".format(full_path)
        # print ("Checking {0} does not exist".format(full_path))
        self.assertFalse(os.path.exists(full_path), err)

    def check_tree_layout(self, tree_path):
        for dname in expected_layout:
            dpath = os.path.join(tree_path, dname)
            self.assertExists(dpath)
            for fname in expected_files:
                fpath = os.path.join(dpath, fname)
                self.assertExists(fpath)
            for fname in unexpected_files:
                fpath = os.path.join(dpath, fname)
                self.assertNotExists(fpath)
        for dname in unexpected_dirs:
            dpath = os.path.join(tree_path, dname)
            self.assertNotExists(dpath)

    def check_versioned_layout(self, versioned_path, expected_trees=None):
        if expected_trees is None:
            expected_trees = _expected_versioned_trees
        self.assertEqual(set(os.listdir(versioned_path)), set(expected_trees))
        for tree in expected_trees:
            tree_path = os.path.join(versioned_path, tree)
            self.check_tree_layout(tree_path)

    def setup_snapshot_layout(self, local_path):
        # Set up one local tree as already FINISHED
        skip_finished = _expected_snapshot_trees[0]
        finished_path = os.path.join(local_path, skip_finished)
        os.makedirs(finished_path)
        mark_trees_finished(local_path, [skip_finished])
        # One tree we expect to be skipped due to a missing STATUS file
        not_ready_path = os.path.join(local_path, _skipped_snapshot_tree)
        # We expect the other trees to be synchronised
        expect_sync = _expected_snapshot_trees[1:]
        return finished_path, expect_sync, not_ready_path


    def check_snapshot_layout(self, snapshot_path, finished_path=None,
                                    expected_paths=(), not_ready_path=None):
        # The tree locally marked as complete should not get updated
        if finished_path is not None:
            self.assertExists(finished_path)
            self.assertEqual(os.listdir(finished_path), ["STATUS"])
        # The tree not remotely marked as complete should not get updated
        if not_ready_path is not None:
            self.assertNotExists(not_ready_path)
        # The other trees should all get synchronised
        previous_tree_path = None
        for tree in expected_paths:
            tree_path = os.path.join(snapshot_path, tree)
            self.check_tree_layout(tree_path)
            if previous_tree_path is not None:
                self.check_tree_cross_links(tree_path, previous_tree_path)
            previous_tree_path = tree_path
            status_path = os.path.join(tree_path, "STATUS")
            self.assertExists(status_path)
            with open(status_path) as f:
                self.assertEqual(f.read().strip(), "FINISHED")

    def check_tree_cross_links(self, tree_path_A, tree_path_B):
        trees = (tree_path_A, tree_path_B)
        for dname in expected_layout:
            dpaths = [os.path.join(tree, dname) for tree in trees]
            map(self.assertExists, dpaths)
            for fname in expected_files:
                fpaths = [os.path.join(dpath, fname) for dpath in dpaths]
                msg = "{0} are different files".format(fpaths)
                self.assertTrue(os.path.samefile(*fpaths), msg)

    def check_stats(self, actual, expected):
        if isinstance(actual, dict):
            actual = sync_trees.SyncStats(**actual)
        for field, expected_value in expected.iteritems():
            actual_value = getattr(actual, field)
            msg_fmt = "sync stats field {0!r} ({1!r} != {2!r})"
            msg = msg_fmt.format(field, actual_value, expected_value)
            self.assertEqual(actual_value, expected_value, msg)

    def check_log_output(self, log_data, expected_result, expected_stats):
        self.assertIn(expected_result, log_data)
        actual_stats = sync_trees.SyncStats.from_rsync_output(log_data)
        self.check_stats(actual_stats, expected_stats)
