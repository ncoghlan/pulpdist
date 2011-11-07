"""Miscellaneous utility functions for Pulp UI (e.g. context processors)"""
from collections import namedtuple
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from .models import PulpServer

# Helpers for class-based views
Breadcrumb = namedtuple("Breadcrumb", "label link")

def get_server(server_slug):
    return get_object_or_404(PulpServer, server_slug=server_slug)

def get_server_url(urlname, server_slug):
    kwargs = {'server_slug' : server_slug}
    return reverse(urlname, kwargs=kwargs)

def get_repo_url(urlname, server_slug, repo_id):
    kwargs = {'server_slug' : server_slug,
              'repo_id' : repo_id,
             }
    return reverse(urlname, kwargs=kwargs)

class ServerMixin(object):
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

    @classmethod
    def get_url(cls, server_slug, repo_id):
        return get_repo_url(cls.urlname, server_slug, repo_id)

    @classmethod
    def breadcrumb(cls, server_slug, repo_id):
        url = mark_safe(cls.get_url(server_slug, repo_id))
        return Breadcrumb(repo_id, url)


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
