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
"""URL definitions for Pulp UI"""

from django.conf.urls.defaults import url, patterns
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth import logout

from .views import MainIndex, ServerView, RepoListView, RepoView

import restapi as api

# Main site
urlpatterns = patterns('',
    url(r'^$',
        login_required(MainIndex.as_view()), name=MainIndex.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/$',
        login_required(ServerView.as_view()), name=ServerView.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/repos/$',
        login_required(RepoListView.as_view()), name=RepoListView.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/repos/(?P<repo_id>\w+)/$',
        login_required(RepoView.as_view()), name=RepoView.urlname),
)

# Authentication handling
def logout_view(request):
    logout(request)
    return redirect(MainIndex.urlname)

urlpatterns += patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'pulpdist/login.tmpl'}, name="pulpdist_login"),
    url(r'^logout/$', logout_view, name="pulpdist_logout"),
)

# REST API

urlpatterns += patterns('',
    api.ResourceIndex.make_url('api'),

    api.PulpServerResourceIndex.make_url('api/servers'),
    api.PulpServerResourceDetail.make_url('api/servers/<server_slug>'),
    api.PulpRepoResourceIndex.make_alias('api/servers/<server_slug>/repos'),
    api.PulpContentTypeResourceIndex.make_alias('api/servers/<server_slug>/content_types'),
    api.PulpDistributorResourceIndex.make_alias('api/servers/<server_slug>/distributors'),
    api.PulpImporterResourceIndex.make_alias('api/servers/<server_slug>/importers'),

    # PulpRepoAggregateIndex.make_url('api/repos'),
    api.PulpRepoResourceIndex.make_url('api/repos/<server_slug>'),
    api.PulpRepoResourceDetail.make_url('api/repos/<server_slug>/<pulp_id>'),
    api.PulpRepoImporterDetail.make_url('api/repos/<server_slug>/<pulp_id>/importer'),
    api.PulpRepoSyncHistoryDetail.make_url('api/repos/<server_slug>/<pulp_id>/sync_history'),

    # restapi.PulpContentTypeAggregateIndex.make_url('api/content_types'),
    api.PulpContentTypeResourceIndex.make_url('api/content_types/<server_slug>'),
    api.PulpContentTypeResourceDetail.make_url('api/content_types/<server_slug>/<pulp_id>'),

    # restapi.PulpDistributorAggregateIndex.make_url('api/distributors'),
    api.PulpDistributorResourceIndex.make_url('api/distributors/<server_slug>'),
    api.PulpDistributorResourceDetail.make_url('api/distributors/<server_slug>/<pulp_id>'),

    # restapi.PulpImporterAggregateIndex.make_url('api/importers'),
    api.PulpImporterResourceIndex.make_url('api/importers/<server_slug>'),
    api.PulpImporterResourceDetail.make_url('api/importers/<server_slug>/<pulp_id>'),

)

