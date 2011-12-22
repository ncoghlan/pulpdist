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
"""Miscellaneous utility functions for Pulp UI (e.g. context processors)"""
from collections import namedtuple
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.conf import settings

from .models import PulpServer

# Easy access to common version definition
def version():
    return "0.1a0"

# Helpers for class-based views
Breadcrumb = namedtuple("Breadcrumb", "label link")

def get_server(server_slug):
    return get_object_or_404(PulpServer, server_slug=server_slug)

def get_url(urlname, **kwds):
    return reverse(urlname, kwargs=kwds)

def get_server_url(urlname, server_slug, **kwds):
    kwds['server_slug'] = server_slug
    return reverse(urlname, kwargs=kwds)

def get_repo_url(urlname, server_slug, repo_id, **kwds):
    kwds['server_slug'] = server_slug
    kwds['repo_id'] = repo_id
    return reverse(urlname, kwargs=kwds)

class ViewMixin(object):
    # Hook to allow behaviour of all PulpDist custom views
    # to be adjusted globally
    pass

class ServerMixin(ViewMixin):
    @property
    def server_slug(self):
        return self.kwargs['server_slug']

    def get_pulp_server(self):
        return get_server(self.server_slug)

    def get_context_data(self, **kwds):
        context = super(ServerMixin, self).get_context_data(**kwds)
        if 'pulp_server' not in context:
            context['pulp_server'] = self.get_pulp_server()
        context.setdefault('breadcrumbs', []).extend(self.get_breadcrumbs())
        return context

    def get_breadcrumbs(self):
        return []

    @classmethod
    def get_url(cls, server_slug):
        return get_server_url(cls.urlname, server_slug)

    @classmethod
    def breadcrumb(cls, site_label, server_slug):
        url = mark_safe(cls.get_url(server_slug))
        return Breadcrumb(site_label, url)


class RepoMixin(ServerMixin):
    @property
    def repo_id(self):
        return self.kwargs['repo_id']

    def get_pulp_repo(self, server=None):
        if server is None:
            server = self.get_pulp_server()
        return server.get_repo(self.repo_id)

    def get_context_data(self, **kwds):
        context = super(RepoMixin, self).get_context_data(**kwds)
        if 'repo_id' not in context:
            context['repo_id'] = self.repo_id
        return context

    @classmethod
    def get_url(cls, server_slug, repo_id):
        return get_repo_url(cls.urlname, server_slug, repo_id)

    @classmethod
    def breadcrumb(cls, display_name, server_slug, repo_id):
        url = mark_safe(cls.get_url(server_slug, repo_id))
        return Breadcrumb(display_name, url)


# Helper for data table views
class _TableView(ListView):
    # Do not instantiate directly
    # subclasses must define queryset, table_type and view_title
    context_object_name='data_as_list'
    template_name='pulpdist/data_table.tmpl'

    def data_unavailable(self, context):
        return "No data available"

    def get_context_data(self, **kwds):
        context = super(_TableView, self).get_context_data(**kwds)
        context['title'] = self.view_title
        data = context['data_as_list']
        if data:
            context['data_as_table'] = self.table_type(data)
        else:
            context['data_unavailable'] = self.table_type.empty_text
        return context
