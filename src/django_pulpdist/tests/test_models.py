"""Basic model tests for Pulp UI Django App"""
from djangosanetesting.cases import DatabaseTestCase

from .. import models
from . import util

from django.conf import settings

class PulpUI_TestCase(DatabaseTestCase):
    def setup(self):
        with util.patch_pulpapi() as api:
            server = models.PulpServer.objects.create(
                         hostname='localhost',
                         pulp_site='Nowhere',
                         server_slug='nowhere',
                         oauth_key='dummy key',
                         oauth_secret='dummy secret')
        self.pulpapi = api

    def test_api_mocked(self):
        self.pulpapi.PulpServer.assert_called()

