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
import httplib

try:
    import json
except ImportError:
    import simplejson as json

from M2Crypto import SSL, httpslib
import oauth2 as oauth

# The pulp client libraries commit a cardinal sin and
# implicitly install a logging handler
# We monkeypatch pulp.client.lib.logutil to prevent this
import pulp.client.lib.logutil
import logging
pulp.client.lib.logutil.getLogger = logging.getLogger
    

import pulp.client.api.server

class _PulpCollection(object):
    def __init__(self, server):
        self._server = server

    @property
    def server(self):
        return self._server

    def get_list(self, queries=None):
        path = self.collection_path
        if queries is None:
            return self.server.GET(path)[1]
        return self.server.GET(path, queries)[1]

    def get_entry(self, entry_id):
        path = "%s/%s/" % (self.collection_path, entry_id)
        return self.server.GET(path)[1]


class PulpRepositories(_PulpCollection):
    collection_path = "/repositories/"

class GenericContentTypes(_PulpCollection):
    collection_path = "/plugins/types/"

class GenericContentImporters(_PulpCollection):
    collection_path = "/plugins/importers/"

class GenericContentDistributors(_PulpCollection):
    collection_path = "/plugins/distributors/"


class PulpServer(pulp.client.api.server.PulpServer):
    # Unlike the standard Pulp client, we support only OAuth over https
    def __init__(self, hostname, oauth_key, oauth_secret):
        super(PulpServer, self).__init__(hostname, path_prefix="/pulp/api/v2")
        self.oauth_consumer = oauth.Consumer(oauth_key, oauth_secret)
        self.oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1

    def _connect(self):
        context = SSL.Context("sslv3")
        connection = httpslib.HTTPSConnection(self.host, self.port, ssl_context=context)
        connection.connect()
        return connection

    def _build_url(self, path, queries=()):
        # base class gets this wrong when path starts with '/'
        if not path.startswith(self.path_prefix):
            if path.startswith('/'):
                sep = ''
            else:
                sep = '/'
            path = sep.join((self.path_prefix, path))
        return super(PulpServer, self)._build_url(path, queries)

    def _request(self, method, path, queries=(), body=None):
        # make a request to the pulp server and return the response
        # NOTE this throws a ServerRequestError if the request did not succeed
        connection = self._connect()
        url = self._build_url(path, queries)
        # Oauth setup
        consumer = self.oauth_consumer
        https_url = 'https://' + self.host + url
        self._log.debug('signing %r request to %r', method, https_url)
        oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method=method, http_url=https_url)
        oauth_request.sign_request(self.oauth_sign_method(), consumer, None)
        self.headers.update(oauth_request.to_header())
        self.headers.update(pulp_user='admin') # TODO: use Django login (eventually Kerberos)
        return super(PulpServer, self)._request(method, path, queries, body)

    def get_repos(self):
        return PulpRepositories(self).get_list()

    def get_repo(self, repo_id):
        return PulpRepositories(self).get_entry(repo_id)

    def get_generic_types(self):
        return GenericContentTypes(self).get_list()

    def get_generic_type(self, type_id):
        return GenericContentTypes(self).get_entry(type_id)

    def get_generic_importers(self):
        return GenericContentImporters(self).get_list()

    def get_generic_importer(self, plugin_id):
        return GenericContentImporters(self).get_entry(plugin_id)

    def get_generic_distributors(self):
        return GenericContentDistributors(self).get_list()

    def get_generic_distributor(self, plugin_id):
        return GenericContentTypes(self).get_entry(plugin_id)
