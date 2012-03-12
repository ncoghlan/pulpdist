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
"""Tests for the PulpDist CLI commands"""

import tempfile
import sys
import contextlib
from cStringIO import StringIO

from .. import commands

from ...core import site_config
from ...core.tests import pulpapi_util, example_site
from ...core.tests.compat import unittest

@contextlib.contextmanager
def capture_stdout():
    saved = sys.stdout
    sys.stdout = output = StringIO()
    try:
        yield output
    finally:
        sys.stdout = saved

# Be warned: this *is* a destructive test that will clobber all repos
# in the local Pulp database...

class BaseTestCase(pulpapi_util.PulpTestCase):

    CONFIG_FILE = tempfile.NamedTemporaryFile()
    CONFIG_FILE.write(example_site.TEST_CONFIG)
    CONFIG_FILE.flush()

    def purge_server(self):
        server = self.server
        for repo in server.get_repos():
            server.delete_repo(repo[u"id"])

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.purge_server()

    def tearDown(self):
        self.purge_server()
        super(BaseTestCase, self).tearDown()

    def assertReposExist(self, repo_list):
        site = site_config.SiteConfig(self.server.get_site_config())
        repo_ids = sorted(r[u"repo_id"] for r in site.get_repo_configs())
        self.assertEqual(repo_ids, repo_list)
        for repo_id in repo_list:
            repo = self.server.get_repo(repo_id)
            self.assertEqual(repo[u"id"], repo_id)

class TestInitialisation(BaseTestCase):
    # Sanity check to ensure "setUp" will work for other test cases
    def test_init(self):
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True)
        cmd = commands.InitialiseRepos(args, self.server)
        with capture_stdout() as output:
            cmd()
        self.assertEqual(output.getvalue(), "")
        self.assertReposExist(example_site.ALL_REPOS)

    def test_init_verbose(self):
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True, verbose=1)
        cmd = commands.InitialiseRepos(args, self.server)
        with capture_stdout() as output:
            cmd()
        output_text = output.getvalue()
        self.assertIn("Added simple_tree importer to raw_sync", output_text)
        self.assertIn("Added simple_tree importer to simple_sync(default)", output_text)
        self.assertIn("Added snapshot_tree importer to snapshot_sync(default)", output_text)
        self.assertIn("Added versioned_tree importer to versioned_sync(other)", output_text)
        self.assertReposExist(example_site.ALL_REPOS)
"""
DeleteRepo
DisableSync
EnableSync
InitialiseRepos
LatestSyncCommand
ModificationCommand
PulpCommand
PulpRepo
PulpServerClient
RepoConfig
RequestSync
ServerRequestError
ShowRepoDetails
ShowRepoStatus
ShowRepoSummary
ShowSyncHistory
ShowSyncLog
ShowSyncStats
SiteConfig
SyncHistoryCommand
ValidateRepoConfig
_cron_sync_repos
_export_repos
"""

if __name__ == '__main__':
    unittest.main()
