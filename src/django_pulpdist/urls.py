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
