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
import pulp.client.api.repository


class RepositoryAPI(pulp.client.api.repository.RepositoryAPI):
    def __init__(self, server):
        self._server = server
        
    @property
    def server(self):
        return self._server


class PulpServer(pulp.client.api.server.PulpServer):
    # Unlike the standard Pulp client, we support only OAuth over https
    def __init__(self, hostname, oauth_key, oauth_secret):
        super(PulpServer, self).__init__(hostname)
        self.oauth_consumer = oauth.Consumer(oauth_key, oauth_secret)
        self.oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1

    def _connect(self):
        context = SSL.Context("sslv3")
        connection = httpslib.HTTPSConnection(self.host, self.port, ssl_context=context)
        connection.connect()
        return connection

    def _request(self, method, path, queries=(), body=None):
        # make a request to the pulp server and return the response
        # NOTE this throws a ServerRequestError if the request did not succeed
        connection = self._connect()
        url = self._build_url(path, queries)
        # Oauth setup
        self._log.debug('signing %r request to %r', method, url)
        consumer = self.oauth_consumer
        https_url = 'https://' + self.host + url
        oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method=method, http_url=https_url)
        oauth_request.sign_request(self.oauth_sign_method(), consumer, None)
        self.headers.update(oauth_request.to_header())
        self.headers.update(pulp_user='admin') # TODO: use Django login (eventually Kerberos)
        return super(PulpServer, self)._request(method, path, queries, body)

    def get_repos(self):
        return RepositoryAPI(self).repositories({})

    def get_repo(self, repo_id):
        return RepositoryAPI(self).repository(repo_id)
