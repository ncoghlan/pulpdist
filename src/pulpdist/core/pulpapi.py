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
import json

from M2Crypto import SSL, httpslib
import oauth2 as oauth

# The pulp client libraries commit a cardinal sin and
# implicitly install a logging handler
# We monkeypatch pulp.client.lib.logutil to prevent this
import pulp.client.lib.logutil
import logging
pulp.client.lib.logutil.getLogger = logging.getLogger


import pulp.client.api.server
import pulp.client.admin.credentials

ServerRequestError = pulp.client.api.server.ServerRequestError

def _response_data(response):
    data = response[1]
    if not isinstance(data, (list, dict)) and data is not True:
        msg = "Expected formatted data, got {0!r}"
        raise ServerRequestError(response[0], msg.format(data))
    return data

class _PulpCollection(object):
    def __init__(self, server):
        self._server = server

    @property
    def server(self):
        return self._server

    def get_list(self, queries=None):
        path = self.collection_path
        if queries is None:
            return _response_data(self.server.GET(path))
        return _response_data(self.server.GET(path, queries))

    def get_entry(self, entry_id):
        path = "%s%s/" % (self.collection_path, entry_id)
        return _response_data(self.server.GET(path))

    def create_entry(self, entry_id, settings):
        path = self.collection_path
        settings["id"] = entry_id
        return _response_data(self.server.POST(path, settings))

    def create_or_save_entry(self, entry_id, settings):
        try:
            return self.create_entry(entry_id, dict(settings))
        except ServerRequestError, ex:
            if ex.args[0] not in (500, 409): # entry already exists
                raise
        return self.save_entry(entry_id, settings)

    def save_entry(self, entry_id, settings):
        path = "%s%s/" % (self.collection_path, entry_id)
        delta = {u"delta": settings}
        return _response_data(self.server.PUT(path, delta))

    def delete_entry(self, entry_id):
        path = "%s%s/" % (self.collection_path, entry_id)
        return self.server.DELETE(path)[0] == 200



class PulpRepositories(_PulpCollection):
    collection_path = "/repositories/"

    def add_importer(self, repo_id, settings):
        path = "%s%s/importers/" % (self.collection_path, repo_id)
        return _response_data(self.server.POST(path, settings))

    def get_importers(self, repo_id):
        path = "%s%s/importers/" % (self.collection_path, repo_id)
        return _response_data(self.server.GET(path))

    def get_sync_history(self, repo_id):
        path = "%s%s/sync_history/" % (self.collection_path, repo_id)
        return _response_data(self.server.GET(path))

    def sync_repo(self, repo_id):
        path = "%s%s/actions/sync/" % (self.collection_path, repo_id)
        return _response_data(self.server.POST(path))

class GenericContentTypes(_PulpCollection):
    collection_path = "/plugins/types/"

class GenericContentImporters(_PulpCollection):
    collection_path = "/plugins/importers/"

class GenericContentDistributors(_PulpCollection):
    collection_path = "/plugins/distributors/"

class PulpServerClient(pulp.client.api.server.PulpServer):
    # Add some convenience methods around the standard
    # pulp-admin client API. Can pass username and password
    # to use Basic Auth, otherwise relies on the certfile
    # created by "pulp-admin auth login"
    def __init__(self, hostname, username=None, password=None):
        super(PulpServerClient, self).__init__(hostname,
                                               path_prefix="/pulp/api/v2")
        if None in (username, password):
            # Rely on certfile
            certfile = pulp.client.admin.credentials.Login().crtpath()
            self.set_ssl_credentials(certfile)
        else:
            # Use basic auth
            self.set_basic_auth_credentials(username, password)


    def _build_url(self, path, queries=()):
        # base class gets this wrong when path starts with '/'
        if not path.startswith(self.path_prefix):
            if path.startswith('/'):
                sep = ''
            else:
                sep = '/'
            path = sep.join((self.path_prefix, path))
        return super(PulpServerClient, self)._build_url(path, queries)

    def get_repos(self):
        return PulpRepositories(self).get_list()

    def get_repo(self, repo_id):
        return PulpRepositories(self).get_entry(repo_id)

    def _repo_settings(self, display_name, description, notes):
        result = {}
        if display_name is not None:
            result[u'display_name'] = display_name
        if description is not None:
            result[u'description'] = description
        if notes is not None:
            result[u'notes'] = notes
        return result

    def create_repo(self, repo_id, display_name=None, description=None, notes=None):
        settings = self._repo_settings(display_name, description, notes)
        return PulpRepositories(self).create_entry(repo_id, settings)

    def create_or_save_repo(self, repo_id, display_name=None, description=None, notes=None):
        settings = self._repo_settings(display_name, description, notes)
        return PulpRepositories(self).create_or_save_entry(repo_id, settings)

    def save_repo(self, repo_id, display_name=None, description=None, notes=None):
        settings = self._repo_settings(display_name, description, notes)
        return PulpRepositories(self).save_entry(repo_id, settings)

    def delete_repo(self, repo_id):
        return PulpRepositories(self).delete_entry(repo_id)

    def get_importer(self, repo_id):
        return self.get_importers(repo_id)[0]

    def get_importers(self, repo_id):
        return PulpRepositories(self).get_importers(repo_id)

    def add_importer(self, repo_id, importer_id, config):
        settings = {
            u'importer_type_id': importer_id,
            u'importer_config': config,
        }
        return PulpRepositories(self).add_importer(repo_id, settings)

    def sync_repo(self, repo_id):
        return PulpRepositories(self).sync_repo(repo_id)

    def get_sync_history(self, repo_id):
        return PulpRepositories(self).get_sync_history(repo_id)

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


class PulpServer(PulpServerClient):
    # Unlike the standard Pulp client, we support only OAuth over https
    def __init__(self, hostname, oauth_key, oauth_secret):
        # Slightly dodgy - want to bypass the PulpServerClient init function
        # TODO: use an API Mixin to make this less dodgy
        super(PulpServerClient, self).__init__(hostname, path_prefix="/pulp/api/v2")
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
        url = self._build_url(path, queries)
        # Oauth setup
        consumer = self.oauth_consumer
        https_url = 'https://' + self.host + url
        self._log.debug('signing %r request to %r', method, https_url)
        oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method=method, http_url=https_url)
        oauth_request.sign_request(self.oauth_sign_method(), consumer, None)
        self.headers['Authorization'] = oauth_request.to_header()['Authorization'].encode('ascii')
        self.headers.update(pulp_user='admin') # TODO: use Django login (eventually Kerberos)
        return super(PulpServer, self)._request(method, path, queries, body)
