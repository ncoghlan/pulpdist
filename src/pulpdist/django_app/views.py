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
"""View definitions for Pulp UI"""

import json

from django.shortcuts import render
from django.views.generic import DetailView
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.html import escape

from django_tables2 import Table, Column

from .util import ViewMixin, ServerMixin, RepoMixin, _TableView, Breadcrumb
from .models import PulpServer

# Repo sync history details
class SyncHistoryTable(Table):
    started = Column()
    completed = Column()

class SyncHistoryView(RepoMixin, _TableView):
    view_title='Repository Sync History'
    urlname = 'pulp_repo_sync_history'
    table_type = SyncHistoryTable
    empty_text = "There are no sync history entries for this repository."

    @property
    def queryset(self):
        server = self.get_pulp_server()
        return server.get_sync_history(self.repo_id)

    def get_breadcrumbs(self):
        server = self.get_pulp_server()
        name = self.get_pulp_repo()['display_name']
        crumbs = [ServerView.breadcrumb(server.pulp_site, server.server_slug),
                  RepoListView.breadcrumb(server.server_slug),
                  RepoView.breadcrumb(name, server.server_slug, self.repo_id),
                  self.breadcrumb(server.server_slug, self.repo_id),]
        return crumbs

    @classmethod
    def breadcrumb(cls, server_slug, repo_id):
        return super(SyncHistoryView, cls).breadcrumb('Sync History', server_slug, repo_id)


# Repo details
class RepoView(RepoMixin, DetailView):
    context_object_name = 'pulp_repo'
    urlname = 'pulp_repo_details'
    template_name='pulpdist/repo.tmpl'

    def pretty_json(self, value):
        return json.dumps(value, indent=2, separators=(',', ': '))

    def get_object(self, queryset=None):
        server = self.get_pulp_server()
        details = self.get_pulp_repo()
        annotations = {}
        for k, v in details["notes"].iteritems():
            annotations[k] = self.pretty_json(v)
        details["annotations"] = annotations
        importer_info = server.get_importer(self.repo_id)
        if importer_info["last_sync"] is None:
            importer_info["last_sync"] = "Never"
        details["importer_info"] = importer_info
        return details

    def get_breadcrumbs(self):
        server = self.get_pulp_server()
        name = self.get_pulp_repo()['display_name']
        crumbs = [ServerView.breadcrumb(server.pulp_site, server.server_slug),
                  RepoListView.breadcrumb(server.server_slug),
                  self.breadcrumb(name, server.server_slug, self.repo_id),]
        return crumbs


# Repos on a server
class RepoTable(Table):
    id = Column(verbose_name='Repo Name')
    description = Column(verbose_name='Description')
    empty_text = "There are no repositories defined in the Pulp server."

    def render_id(self, record):
        repo_id = record['id']
        kwargs = {
            'repo_id' : repo_id,
            'server_slug' : record['server_slug'],
        }
        repo_name = record['display_name']
        url = reverse(RepoView.urlname, kwargs=kwargs)
        link = '<a href="{0}">{1}</a>'.format(url, repo_name)
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
        return super(RepoListView, cls).breadcrumb('Repositories', server_slug)


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
        link = '<a href="{0}">{1}</a>'.format(url, link_text)
        return mark_safe(link)


# Main index
class ServerTable(Table):
    pulp_site = Column(verbose_name='Pulp Site')
    hostname = Column()
    empty_text = "There are no Pulp servers configured."

    def render_pulp_site(self, record):
        return ServerView.make_link(record.pulp_site, record.server_slug)

class ServerListView(ViewMixin, _TableView):
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
