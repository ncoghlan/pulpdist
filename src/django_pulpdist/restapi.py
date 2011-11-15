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
"""REST API definitions for Pulp UI"""
import collections 
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.http import Http404

from djangorestframework.views import View, ListOrCreateModelView, InstanceModelView
from djangorestframework.resources import Resource, ModelResource
from djangorestframework.renderers import DocumentingHTMLRenderer

from .models import PulpServer
from .forms import PulpServerForm
from .util import get_server, get_server_url, get_repo_url, get_url

def api_link(relationship, url):
    return dict(_type="link", url=url, rel=relationship)

SERVER_COLLECTION = "collection/servers"
SERVER_RESOURCE = "resource/server"
REPO_COLLECTION = "collection/repos"
REPO_RESOURCE = "resource/repo"
CONTENT_TYPE_COLLECTION = "collection/content_types"
CONTENT_TYPE_RESOURCE = "resource/content_type"
IMPORTER_COLLECTION = "collection/importers"
IMPORTER_RESOURCE = "resource/importer"
DISTRIBUTOR_COLLECTION = "collection/distributors"
DISTRIBUTOR_RESOURCE = "resource/distributor"

# Resource Index
DocumentingHTMLRenderer.template = "pulpdist/browse_rest.tmpl"

class ResourceIndex(View):
    urlname = "restapi_root"

    def get(self, request):
        return {
            "description": "REST API for Pulp Web UI",
            "servers": api_link(
                SERVER_COLLECTION,
                reverse(PulpServerResourceIndex.urlname)),
        }

# Pulp Servers
class PulpServerResource(ModelResource):
    model = PulpServer
    form = PulpServerForm

    def url(self, server):
        return get_server_url(PulpServerResourceView.urlname, server.server_slug)

    def serialize(self, obj):
        data = super(PulpServerResource, self).serialize(obj)
        if isinstance(obj, PulpServer):
            data["_type"] = "pulp_server"
            data["id"] = data.pop("server_slug")
            del data["oauth_secret"]
            data["repositories"] = api_link(
                REPO_COLLECTION,
                get_server_url(PulpRepoResourceIndex.urlname, obj.server_slug))
            data["content_types"] = api_link(
                CONTENT_TYPE_COLLECTION,
                get_server_url(PulpContentTypeResourceIndex.urlname, obj.server_slug))
            #data["importers"] = api_link(
                #IMPORTER_COLLECTION,
                #get_server_url(PulpImporterResourceIndex.urlname, obj.server_slug))
            #data["distributors"] = api_link(
                #DISTRIBUTOR_COLLECTION,
                #get_server_url(PulpDistributorResourceIndex.urlname, obj.server_slug))
        return data

    def get_server_slug(self, data):
        # Handle 'get'/'delete' case
        try:
            server_slug = data["id"]
        except KeyError:
            # Handle 'put'/'post' case
            try:
                pulp_site = data["pulp_site"]
            except KeyError:
                server_slug = None
            else:
                server_slug = slugify(pulp_site)
        return server_slug
        
    def get_bound_form(self, data=None, files=None, method=None):
        if isinstance(data, collections.Mapping):
            server_slug = self.get_server_slug(data)
            if server_slug is not None:
                try:
                    model = get_server(server_slug)
                except Http404:
                    # Creating a new server instance
                    pass
                else:
                    adjusted = data.copy()
                    adjusted["oauth_secret"] = model.oauth_secret
                    return self.form(data=adjusted, instance=model)
        return super(PulpServerResource, self).get_bound_form(data, files, method)

class PulpServerResourceIndex(ListOrCreateModelView):
    resource = PulpServerResource
    urlname = "restapi_pulp_servers"

class PulpServerResourceView(InstanceModelView):
    resource = PulpServerResource
    urlname = "restapi_pulp_server_detail"


# Pulp Repos
class PulpRepoResource(Resource):
    pass

def make_repo_metadata(server_slug, raw):
    backlink = get_server_url(PulpServerResourceView.urlname, server_slug)
    repo_id = raw.pop("id")
    raw["keys_ref"] = raw.pop("keys")
    raw.pop("_id")
    return {
      "_type": "pulp_repo",
      "id": repo_id,
      "url": get_repo_url(PulpRepoResourceView.urlname, server_slug, repo_id),
      "server": api_link(SERVER_RESOURCE, backlink),
      "other_metadata": raw,
    }

class PulpRepoResourceIndex(View):
    urlname = "restapi_pulp_repos"
    def get(self, request, server_slug):
        data = get_server(server_slug).server.get_repos()
        return [make_repo_metadata(server_slug, repo) for repo in data]

class PulpRepoResourceView(View):
    urlname = "restapi_pulp_repo_detail"
    def get(self, request, server_slug, repo_id):
        repo = get_server(server_slug).server.get_repo(repo_id)
        return make_repo_metadata(server_slug, repo)

# Pulp Content Types
class PulpContentTypeResource(Resource):
    pass

def make_content_type_metadata(server_slug, raw):
    backlink = get_server_url(PulpServerResourceView.urlname, server_slug)
    type_id = raw.pop("id")
    raw.pop("_id")
    return {
      "_type": "pulp_content_type",
      "id": type_id,
      "url": get_server_url(PulpContentTypeResourceView.urlname, server_slug, type_id=type_id),
      "server": api_link(SERVER_RESOURCE, backlink),
      "other_metadata": raw,
    }

class PulpContentTypeResourceIndex(View):
    urlname = "restapi_pulp_content_types"
    def get(self, request, server_slug):
        data = get_server(server_slug).server.get_generic_types()
        return [make_content_type_metadata(server_slug, content_type) for content_type in data]

class PulpContentTypeResourceView(View):
    urlname = "restapi_pulp_content_type_detail"
    def get(self, request, server_slug, type_id):
        content_type = get_server(server_slug).server.get_generic_type(type_id)
        return make_content_type_metadata(server_slug, content_type)
        