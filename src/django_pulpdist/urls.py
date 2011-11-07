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

from django.conf.urls.defaults import *

from .views import MainIndex, ServerView, RepoListView, RepoView

from .restapi import (ResourceIndex,
                      PulpServerResourceIndex, PulpServerResourceView,
                      PulpRepoResourceIndex, PulpRepoResourceView)

# Main site
urlpatterns = patterns('',
    url(r'^$',
        MainIndex.as_view(), name=MainIndex.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/$',
        ServerView.as_view(), name=ServerView.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/repos/$',
        RepoListView.as_view(), name=RepoListView.urlname),
    url(r'^server/(?P<server_slug>[-\w]+)/repos/(?P<repo_id>\w+)/$',
        RepoView.as_view(), name=RepoView.urlname),
)

# REST API
urlpatterns += patterns('',
    url(r'^api/$',
        ResourceIndex.as_view(), name=ResourceIndex.urlname),
    url(r'^api/servers/$',
        PulpServerResourceIndex.as_view(), name=PulpServerResourceIndex.urlname),
    url(r'^api/servers/(?P<server_slug>[-\w]+)/$',
        PulpServerResourceView.as_view(), name=PulpServerResourceView.urlname),
    url(r'^api/servers/(?P<server_slug>[-\w]+)/repos/$',
        PulpRepoResourceIndex.as_view(), name=PulpRepoResourceIndex.urlname),
    url(r'^api/servers/(?P<server_slug>[-\w]+)/repos/(?P<repo_id>\w+)$',
        PulpRepoResourceView.as_view(), name=PulpRepoResourceView.urlname),
)
