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
from django.conf.urls.defaults import url
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


class BaseView(View):
    """Base class for all PulpDist REST API views"""
    @classmethod
    def _make_regex(cls, url_parts):
        regex_parts = []
        for part in url_parts.split('/'):
            if part == '<server_slug>':
                part = r'(?P<server_slug>[-\w]+)'
            elif part.startswith('<'):
                part = part.replace('<', r'(?P<')
                part = part.replace('>', r'>\w+)')
            regex_parts.append(part)
        regex_parts.append('$')
        return  '^' + '/'.join(regex_parts)

    @classmethod
    def make_url(cls, url_parts):
        return url(cls._make_regex(url_parts), cls.as_view(), name=cls.urlname)

    @classmethod
    def make_alias(cls, url_parts):
        return url(cls._make_regex(url_parts), cls.as_view())

# Resource Index
DocumentingHTMLRenderer.template = "pulpdist/browse_rest.tmpl"

VERSION = "0.1"

class ResourceIndex(BaseView):
    urlname = "restapi_root"

    def get(self, request):
        return {
            "description": "REST API for PulpDist",
            "version": VERSION,
            "servers": api_link(
                SERVER_COLLECTION,
                reverse(PulpServerResourceIndex.urlname)),
        }

# Pulp Servers
class PulpServerResource(ModelResource):
    model = PulpServer
    form = PulpServerForm

    def url(self, server):
        return get_server_url(PulpServerResourceDetail.urlname, server.server_slug)

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
            data["importers"] = api_link(
                IMPORTER_COLLECTION,
                get_server_url(PulpImporterResourceIndex.urlname, obj.server_slug))
            data["distributors"] = api_link(
                DISTRIBUTOR_COLLECTION,
                get_server_url(PulpDistributorResourceIndex.urlname, obj.server_slug))
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

class PulpServerResourceIndex(ListOrCreateModelView, BaseView):
    resource = PulpServerResource
    urlname = "restapi_pulp_servers"

class PulpServerResourceDetail(InstanceModelView, BaseView):
    resource = PulpServerResource
    urlname = "restapi_pulp_server_detail"



# Pass through cleaned up resources from the Pulp servers
_DICT_ATTRS = dir(dict)

class _IndirectResource(object):
    """Indirect resources correspond to Pulp REST API resources"""
    resource_type = None   # Set by subclass
    index_urlname = None   # Set by subclass
    detail_urlname = None  # Optionally set by subclass
    pulp_path = None       # Set by subclass

    @classmethod
    def _make_metadata(cls, server_slug, raw):
        # Extract the resource identifier
        pulp_id = raw.pop("id")
        # We always link back to the associated server detail API
        backlink = get_server_url(PulpServerResourceDetail.urlname, server_slug)
        # The REST framework gets upset if dict attributes are used as keys
        # so we sanitise any affected Pulp keys by appending an underscore
        for k in _DICT_ATTRS:
            if k in raw:
                safe_key = k + "_"
                raw[safe_key] = raw.pop(k)
        data = {
            "_type": cls.resource_type,
            "server": api_link(SERVER_RESOURCE, backlink),
            "id": pulp_id,
            "pulp_metadata": raw
        }
        detail_url = cls._get_detail_url(server_slug, pulp_id)
        if detail_url is not None:
            data["url"] = detail_url
        return data


    @classmethod
    def _get_index_data(cls, pulp_server, server_slug):
        path = cls.pulp_path
        data = pulp_server.GET(path)[1]
        return [cls._make_metadata(server_slug, detail) for detail in data]

    @classmethod
    def _get_detail_data(cls, pulp_server, server_slug, pulp_id):
        path = cls.pulp_path + pulp_id
        data = pulp_server.GET(path)[1]
        return cls._make_metadata(server_slug, data)

    @classmethod
    def _get_detail_url(cls, server_slug, pulp_id):
        urlname = cls.detail_urlname
        if urlname is None:
            return None
        return get_server_url(urlname, server_slug, pulp_id=pulp_id)

    @classmethod
    def _make_index_view(cls):
        class IndirectIndexView(BaseView):
            urlname = cls.index_urlname
            def get(self, request, server_slug):
                pulp_server = get_server(server_slug).server
                data = cls._get_index_data(pulp_server, server_slug)
                return data
        IndirectIndexView.__name__ = cls.__name__ + "Index"
        return IndirectIndexView

    @classmethod
    def _make_detail_view(cls):
        class IndirectDetailView(BaseView):
            urlname = cls.detail_urlname
            def get(self, request, server_slug, pulp_id):
                pulp_server = get_server(server_slug).server
                data = cls._get_detail_data(pulp_server, server_slug, pulp_id)
                return data
        IndirectDetailView.__name__ = cls.__name__ + "Detail"
        return IndirectDetailView

# Pulp Repos
class PulpRepoResource(_IndirectResource):
    resource_type = "pulp_repo"
    index_urlname = "restapi_pulp_repos"
    detail_urlname = "restapi_pulp_repo_detail"
    pulp_path = "/repositories/"

PulpRepoResourceIndex = PulpRepoResource._make_index_view()
PulpRepoResourceDetail = PulpRepoResource._make_detail_view()

# Pulp Content Types
class PulpContentTypeResource(_IndirectResource):
    resource_type = "pulp_content_type"
    index_urlname = "restapi_pulp_content_types"
    # detail_urlname = "restapi_pulp_content_type_detail"
    pulp_path = "/plugins/types/"

PulpContentTypeResourceIndex = PulpContentTypeResource._make_index_view()
PulpContentTypeResourceDetail = PulpContentTypeResource._make_detail_view()

# Pulp Distributor Plugins
class PulpDistributorResource(_IndirectResource):
    resource_type = "pulp_distributor"
    index_urlname = "restapi_pulp_distributors"
    # detail_urlname = "restapi_pulp_distributor_detail"
    pulp_path = "/plugins/distributors/"

PulpDistributorResourceIndex = PulpDistributorResource._make_index_view()
PulpDistributorResourceDetail = PulpDistributorResource._make_detail_view()

# Pulp Importer Plugins
class PulpImporterResource(_IndirectResource):
    resource_type = "pulp_importer"
    index_urlname = "restapi_pulp_importers"
    # detail_urlname = "restapi_pulp_importer_detail"
    pulp_path = "/plugins/importers/"

PulpImporterResourceIndex = PulpImporterResource._make_index_view()
PulpImporterResourceDetail = PulpImporterResource._make_detail_view()
