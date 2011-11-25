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

import unittest
import shutil
import tempfile
import os.path

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

expected_versioned_trees = [u"relevant-{}".format(i) for i in range(1, 5)]

source_trees = [
    u"simple",
    u"versioned/ignored",
    u"versioned/relevant-but-not-really",
]

source_trees.extend(os.path.join(u"versioned", tree) for tree in expected_versioned_trees)

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
    remote_path = u"/test_data/versioned/",
    version_pattern = u"relevant*",
    excluded_versions = u"relevant-but*".split(),
    excluded_files = u"*skip*".split(),
    sync_filters = u"exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

def start_rsyncd():
    rsyncd = rsync_daemon.RsyncDaemon(test_data_layout, test_files)
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
        err = "{} does not exist".format(full_path)
        # print ("Checking {} exists".format(full_path))
        self.assertTrue(os.path.exists(full_path), err)

    def assertNotExists(self, full_path):
        err = "{} exists".format(full_path)
        # print ("Checking {} does not exist".format(full_path))
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

    def check_tree_cross_links(self, tree_path_A, tree_path_B):
        trees = (tree_path_A, tree_path_B)
        for dname in expected_layout:
            dpaths = [os.path.join(tree, dname) for tree in trees]
            map(self.assertExists, dpaths)
            for fname in expected_files:
                fpaths = [os.path.join(dpath, fname) for dpath in dpaths]
                msg = "{} are different files".format(fpaths)
                self.assertTrue(os.path.samefile(*fpaths))

    def mark_trees_finished(self, base_path, trees):
        for tree in trees:
            status_path = os.path.join(base_path, tree, u"STATUS")
            with open(status_path, 'w') as f:
                f.write("FINISHED\n")

