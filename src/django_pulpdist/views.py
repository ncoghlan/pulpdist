"""View definitions for Pulp UI"""

from django.shortcuts import render
from django.views.generic import DetailView
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.html import escape

from django_tables2 import Table, Column

from .util import ServerMixin, RepoMixin, _TableView, Breadcrumb
from .models import PulpServer

# Repo details
class RepoView(RepoMixin, DetailView):
    context_object_name = 'pulp_repo'
    urlname = 'pulp_repo_details'
    template_name='pulpdist/repo.tmpl'

    def get_object(self, queryset=None):
        return self.get_pulp_repo()

    def get_breadcrumbs(self):
        server = self.get_pulp_server()
        crumbs = [ServerView.breadcrumb(server.pulp_site, server.server_slug),
                  RepoListView.breadcrumb(server.server_slug),
                  self.breadcrumb(server.server_slug, self.repo_id),]
        return crumbs


# Repos on a server
class RepoTable(Table):
    id = Column(verbose_name='Repo Name')
    distribution = Column()
    uri_ref = Column(verbose_name='Repo URL')
    empty_text = "There are no repositories defined in the Pulp server."

    def render_id(self, record):
        repo_id = record['id']
        kwargs = {
            'repo_id' : repo_id,
            'server_slug' : record['server_slug'],
        }
        repo_name = escape(repo_id)
        url = reverse(RepoView.urlname, kwargs=kwargs)
        link = '<a href="{}">{}</a>'.format(url, repo_name)
        return mark_safe(link)


class RepoListView(ServerMixin, _TableView):
    table_type = RepoTable
    view_title = 'Repositories'
    urlname = 'pulp_repo_index'

    @property
    def queryset(self):
        server = self.get_pulp_server()
        print "Retrieving repo data from Pulp server"
        return server.get_repos()

    def get_breadcrumbs(self):
        server = self.get_pulp_server()
        crumbs = [ServerView.breadcrumb(server.pulp_site, server.server_slug),
                  self.breadcrumb(server.server_slug),]
        return crumbs

    @classmethod
    def breadcrumb(cls, server_slug):
        url = mark_safe(cls.get_url(server_slug))
        return Breadcrumb('Repositories', url)


# Server details
class ServerView(ServerMixin, DetailView):
    context_object_name = 'pulp_server'
    urlname = 'pulp_server_details'
    template_name='pulpdist/server.tmpl'

    def get_object(self):
        return self.get_pulp_server()

    def get_breadcrumbs(self):
        server = self.get_pulp_server()
        return [self.breadcrumb(server.pulp_site, server.server_slug)]

    @classmethod
    def make_link(cls, link_text, server_slug):
        url = cls.get_url(server_slug)
        link_text = escape(link_text)
        link = '<a href="{}">{}</a>'.format(url, link_text)
        return mark_safe(link)


# Main index
class ServerTable(Table):
    pulp_site = Column(verbose_name='Pulp Site')
    hostname = Column()
    empty_text = "There are no Pulp servers configured."

    def render_pulp_site(self, record):
        return ServerView.make_link(record.pulp_site, record.server_slug)

class ServerListView(_TableView):
    table_type = ServerTable
    view_title = 'Pulp Servers'
    urlname = 'pulp_server_index'
    queryset = PulpServer.objects.all()

class MainIndex(ServerListView):
    urlname = 'pulpdist_root_index'
    template_name='pulpdist/index.tmpl'

    def get_context_data(self, **kwds):
        context = super(MainIndex, self).get_context_data(**kwds)
        context['title'] = 'Home'
        return context
