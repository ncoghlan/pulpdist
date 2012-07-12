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
    result = Column(accessor="summary.result", default="PLUGIN_ERROR")
    started = Column()
    completed = Column()
    empty_text = "There are no sync history entries for this repository."

class SyncHistoryView(RepoMixin, _TableView):
    table_type = SyncHistoryTable
    view_title='Repository Sync History'
    urlname = 'pulp_repo_sync_history'

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

    def format_entries(self, data):
        formatted = {}
        for k, v in data.iteritems():
            formatted[k] = self.pretty_json(v)
        return formatted

    def get_object(self, queryset=None):
        server = self.get_pulp_server()
        details = self.get_pulp_repo()
        details["annotations"] = self.format_entries(details["notes"])
        importer = details["importer_info"] = server.get_importer(self.repo_id)
        if importer:
            raw_config = importer["config"]
            formatted_config = self.format_entries(raw_config)
            details["importer_config"] = sorted(formatted_config.iteritems())
        log_url = "{0}/{1}.log".format(server.server.get_sync_logs_url(),
                                       self.repo_id)
        details["latest_sync_log_url"] = log_url
        sync_history = server.get_sync_history(self.repo_id)
        if sync_history:
            last_sync = sync_history[0]
            details["last_sync_attempt"] = last_sync["started"]
            summary = last_sync.get("summary")
            if summary:
                last_status = summary["result"]
            else:
                last_status = "PLUGIN_ERROR"
            details["last_status"] = last_status
        else:
            details["last_sync_attempt"] = "Never"
            details["last_status"] = "N/A"
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
    display_name = Column(verbose_name='Repo Name')
    description = Column()
    sync_enabled = Column(verbose_name="Sync Enabled?")
    last_status = Column()
    last_sync_attempt = Column()
    sync_in_progress = Column(accessor="importer.sync_in_progress",
                              verbose_name="Sync in Progress?")
    empty_text = "There are no repositories defined in the Pulp server."

    def __init__(self, data):
        super(RepoTable, self).__init__(data)
        for record in data:
            # Add a few derived fields
            self.set_sync_enabled(record)
            self.set_last_status(record)
            self.set_last_sync_attempt(record)

    def render_display_name(self, record):
        repo_id = record['id']
        kwargs = {
            'repo_id' : repo_id,
            'server_slug' : record['server_slug'],
        }
        repo_name = record['display_name']
        url = reverse(RepoView.urlname, kwargs=kwargs)
        link = '<a href="{0}">{1}</a>'.format(url, repo_name)
        return mark_safe(link)

    def set_sync_enabled(self, record):
        status = "-"
        importer = record["importer"]
        if importer:
            config = importer["config"]
            if config.get("enabled"):
                status = "TEST" if config.get("dry_run_only") else "ENABLED"
        record["sync_enabled"] = status

    def set_last_status(self, record):
        status = None
        history = record["sync_history"]
        if history:
            status = history[0]["summary"]["result"]
        record["last_status"] = status

    def set_last_sync_attempt(self, record):
        start = None
        history = record["sync_history"]
        if history:
            start = history[0]["started"]
        record["last_sync_attempt"] = start


class RepoListView(ServerMixin, _TableView):
    table_type = RepoTable
    view_title = 'Repositories'
    urlname = 'pulp_repo_index'

    @property
    def queryset(self):
        server = self.get_pulp_server()
        repos = server.get_repos()
        for repo in repos:
            repo_id = repo["id"]
            repo["sync_history"] = server.get_sync_history(repo_id, 1)
            repo["importer"] = server.get_importer(repo_id)
        return repos

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
