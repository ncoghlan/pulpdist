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
import tempfile
import os.path

from .compat import unittest

from . import rsync_daemon

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

_expected_versioned_trees = [u"relevant-{0}".format(i) for i in range(1, 5)]

source_trees = [
    u"simple",
    u"versioned/ignored",
    u"versioned/relevant-but-not-really",
    u"snapshot/ignored",
    u"snapshot/relevant-but-not-really",
]

source_trees.extend(os.path.join(u"versioned", tree) for tree in _expected_versioned_trees)
source_trees.extend(os.path.join(u"snapshot", tree) for tree in _expected_versioned_trees)

test_trees_finished = [os.path.join(u"snapshot", tree) for tree in _expected_versioned_trees[:-1]]

test_data_layout = [
    os.path.join(tree_dir, subdir)
        for tree_dir in source_trees
            for subdir in source_layout
]

_default_log = u"/dev/null"

CONFIG_TREE_SYNC = dict(
    tree_name = u"Simple Tree",
    remote_server = u"localhost",
    remote_path = u"/test_data/simple/",
    excluded_files = u"*skip*".split(),
    sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

CONFIG_VERSIONED_SYNC = dict(
    tree_name = u"Versioned Tree",
    remote_server = u"localhost",
    remote_path = u"/test_data/versioned/",
    version_pattern = u"relevant*",
    excluded_versions = u"relevant-but*".split(),
    excluded_files = u"*skip*".split(),
    sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

CONFIG_SNAPSHOT_SYNC = dict(
    tree_name = u"Snapshot Tree",
    remote_server = u"localhost",
    remote_path = u"/test_data/snapshot/",
    version_pattern = u"relevant*",
    excluded_versions = u"relevant-but*".split(),
    excluded_files = u"*skip*".split(),
    sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)


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

def start_rsyncd():
    rsyncd = rsync_daemon.RsyncDaemon(make_layout)
    rsyncd.start()
    return rsyncd

class TreeTestCase(unittest.TestCase):
    def setUp(self):
        self.rsyncd = rsyncd = start_rsyncd()
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

    def check_versioned_layout(self, versioned_path):
        for tree in _expected_versioned_trees:
            tree_path = os.path.join(versioned_path, tree)
            self.check_tree_layout(tree_path)

    def setup_snapshot_layout(self, local_path):
        # Set up one local tree as already FINISHED
        skip_finished = _expected_versioned_trees[0]
        finished_path = os.path.join(local_path, skip_finished)
        os.makedirs(finished_path)
        mark_trees_finished(local_path, [skip_finished])
        # We expect most of the trees to be sync'ed
        expect_sync = _expected_versioned_trees[1:-1]
        # The last tree we expect to be skipped
        skip_not_ready = _expected_versioned_trees[-1]
        not_ready_path = os.path.join(local_path, skip_not_ready)
        return finished_path, expect_sync, not_ready_path


    def check_snapshot_layout(self, snapshot_path, finished_path,
                                    expected_paths, not_ready_path):
        # The tree locally marked as complete should not get updated
        self.assertExists(finished_path)
        self.assertEqual(os.listdir(finished_path), ["STATUS"])
        # The tree not remotely marked as complete should not get updated
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
                self.assertTrue(os.path.samefile(*fpaths))
