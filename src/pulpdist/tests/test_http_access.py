"""HTTP Access Tests for Pulp Web UI"""
from djangosanetesting.cases import HttpTestCase

# Needs a live server to back the web API

class Index_TestCase(HttpTestCase):
    fixtures = ['pulpdist/fixtures/pulpdist_server_details.json']
    
    def test_index_loads(self):
        resp = self.client.get('/pulpdist/')
        self.assertEqual(resp.status_code, 200)