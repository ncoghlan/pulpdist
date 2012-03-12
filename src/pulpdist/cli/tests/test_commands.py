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

DISPLAY_IDS = {
    "raw_sync": "raw_sync",
    "simple_sync__default": "simple_sync(default)",
    "snapshot_sync__default": "snapshot_sync(default)",
    "versioned_sync__other": "versioned_sync(other)",
}

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

    def get_cmd_output(self, cmd):
        with capture_stdout() as output:
            cmd()
        output.seek(0)
        return output


class TestUninitialised(BaseTestCase):
    # Test the init and validate commands

    def test_init(self):
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True)
        cmd = commands.InitialiseRepos(args, self.server)
        output_text = self.get_cmd_output(cmd).getvalue()
        self.assertEqual(output_text, "")
        self.assertReposExist(example_site.ALL_REPOS)

    def test_init_verbose(self):
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True, verbose=1)
        cmd = commands.InitialiseRepos(args, self.server)
        output_text = self.get_cmd_output(cmd).getvalue()
        for repo_id in example_site.ALL_REPOS:
            importer_type = example_site.IMPORTER_TYPES[repo_id]
            display_id = DISPLAY_IDS[repo_id]
            msg = "Added {0} importer to {1}".format(importer_type, display_id)
            self.assertIn(msg, output_text)
        self.assertReposExist(example_site.ALL_REPOS)

    def test_validate(self):
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True)
        cmd = commands.ValidateRepoConfig(args, self.server)
        output_text = self.get_cmd_output(cmd).getvalue()
        for repo_id in example_site.ALL_REPOS:
            display_id = DISPLAY_IDS[repo_id]
            msg = "Config for {0} is valid".format(display_id)
            self.assertIn(msg, output_text)
        self.assertReposExist([])


class InitialisedTestCase(BaseTestCase):
    # Base test case for tests that need the repos initialised first

    def setUp(self):
        super(InitialisedTestCase, self).setUp()
        args = commands.make_args(config_fname=self.CONFIG_FILE.name,
                                  force=True)
        commands.InitialiseRepos(args, self.server)()


class TestBasicCommands(InitialisedTestCase):

    def test_repo_summary(self):
        args = commands.make_args()
        cmd = commands.ShowRepoSummary(args, self.server)
        output = self.get_cmd_output(cmd)
        lines = iter(output)
        for line in lines:
            self.assertTrue(line.startswith("Repositories defined"))
            break
        seen = []
        expected = example_site.ALL_REPOS
        for line, repo_id in zip(lines, expected):
            self.assertTrue(line.startswith(DISPLAY_IDS[repo_id]))
            seen.append(repo_id)
        self.assertEqual(seen, expected)

    def test_repo_details(self):
        args = commands.make_args()
        cmd = commands.ShowRepoDetails(args, self.server)
        output = self.get_cmd_output(cmd)
        seen = []
        expected = example_site.ALL_REPOS
        def expected_id():
            repo_id = expected[len(seen)]
            return repo_id, DISPLAY_IDS[repo_id]
        for line in output:
            if line.startswith("Repository details for"):
                repo_id, display_id = expected_id()
                self.assertIn(display_id, line)
                seen.append(repo_id)
        self.assertEqual(seen, expected)

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
