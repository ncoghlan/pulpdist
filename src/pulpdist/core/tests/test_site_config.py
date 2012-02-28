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
from .. import site_config, site_sql

class TestSiteConfig(unittest.TestCase):

    def test_db_session(self):
        # Quick sanity check on the DB schema
        config = site_config.SiteConfig()
        session = config.get_db_session()
        sync_types = session.query(site_sql.SyncType).order_by('sync_type')
        self.assertEqual([r.sync_type for r in sync_types], sorted(site_sql.SYNC_TYPES))

if __name__ == '__main__':
    unittest.main()
