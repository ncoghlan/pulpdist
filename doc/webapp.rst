.. _web-application:

PulpDist Web Application
========================

The PulpDist web application is a Django-based web service that can be set
up to monitor a network of Pulp servers.

Early iterations will focus purely on status monitoring, leaving
configuration tasks to command line scripting tools. Longer term,
some configuration tasks may be permitted through the web application
(there are many steps to be taken before that will be possible, such
as implementing a robust authorisation scheme).


REST API
--------

The Rest API is relative to the assigned base URL for the ``django_pulpdist``
application (``/pulpdist/`` by default)::

    api/  # API root

    api/servers/                           # All configured Pulp servers
    api/servers/<server_id>/               # Specific server
    api/servers/<server_id>/repos          # -> api/repos/<server_id>
    api/servers/<server_id>/content_types  # -> api/content_types/<server_id>
    api/servers/<server_id>/distributors   # -> api/distributors/<server_id>
    api/servers/<server_id>/importers      # -> api/importers/<server_id>

    api/repos                                      # All repos on all servers
    api/repos/<server_id>/                         # All repos on server
    api/repos/<server_id>/<repo_id>/               # Specific repo
    api/repos/<server_id>/<repo_id>/content_types  # Assigned content types
    api/repos/<server_id>/<repo_id>/importer       # Assigned importer
    api/repos/<server_id>/<repo_id>/distributors   # Assigned distributors
    api/repos/<server_id>/<repo_id>/sync           # Sync config & status

    api/content_types                         # All content types on all servers
    api/content_types/<server_id>/            # All content types on server
    api/content_types/<server_id>/<type_id>/  # Specific content type definition

    api/distributors                           # All distributors on all servers
    api/distributors/<server_id>/              # All distributors on server
    api/distributors/<server_id>/<plugin_id>/  # Specific distributor definition

    api/importers                           # All importers on all servers
    api/importers/<server_id>/              # All importers on server
    api/importers/<server_id>/<plugin_id>/  # Specific importer definition
