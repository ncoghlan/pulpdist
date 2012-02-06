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

from django.conf.urls.defaults import patterns, include, url
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login
from django.contrib.auth import logout
from django.contrib import admin
from django.shortcuts import redirect

from .views import MainIndex, ServerView, RepoListView, RepoView, SyncHistoryView

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
    url(r'^server/(?P<server_slug>[-\w]+)/repos/(?P<repo_id>\w+)/sync_history$',
        login_required(SyncHistoryView.as_view()), name=SyncHistoryView.urlname),
)

# Authentication handling
def logout_view(request):
    logout(request)
    return redirect(MainIndex.urlname)

class PulpDistAuthenticationForm(AuthenticationForm):
    allow_local_auth = settings.ENABLE_DUMMY_AUTH
    if allow_local_auth:
        dummy_user = settings.DUMMY_AUTH_USER

def login_view(request):
    return login(request,
                 template_name='pulpdist/login.tmpl',
                 authentication_form=PulpDistAuthenticationForm)

urlpatterns += patterns('',
    url(r'^login/$', login_view, name="pulpdist_login"),
    url(r'^logout/$', logout_view, name="pulpdist_logout"),
)

# Admin site

admin.autodiscover()
admin.site.login_template = 'pulpdist/login.tmpl'
admin.site.login_form = PulpDistAuthenticationForm

urlpatterns += patterns('',
    # Hook up the admin pages
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
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

