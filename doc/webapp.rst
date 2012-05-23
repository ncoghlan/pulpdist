.. _web-application:

PulpDist Web Application
========================

The PulpDist web application is a Django-based web service that can be set
up to monitor a network of Pulp servers.

Current iterations focus primarily on status monitoring, leaving
configuration tasks to command line scripting tools. Longer term,
some configuration tasks may be permitted through forms in the web
application.

This page focuses on deployment of a single PulpDist web app instance with
a colocated Pulp server. Other configurations are of course possible - the
two communicate solely through the Pulp REST API (Note: the PulpDist web app
does not yet cache results received from the Pulp server, nor has it been
optimised to make full use of server side batch queries and filtering, so
expect poor performance from the current version if the two aren't running on
the same web server and abysmal performance if they aren't at least on the same
LAN).

Deployment
----------

The first step in deploying a standard PulpDist web application with a
colocated Pulp server is::

   $ sudo yum install pulpdist-plugins pulpdist-httpd

(Note: prebuilt RPMs are not yet available from the public repo. See
:ref:`building-rpms`)

If you're using a custom Django settings file, then package that as an RPM
with a dependency on ``pulpdist-django`` and install the custom RPM instead
of ``pulpdist-httpd``. More on that below.

After installation, a few configuration settings need to be adjusted.

#. Update ``/etc/pulp/pulp.conf`` in accordance with the `Pulp Installation
   Guide`_, including:

   * setting up `OAuth authentication`_
   * setting up `LDAP user authentication`_
   * changing the default password
   * Ensure the file is not world-readable (as both the OAuth key and the
     admin password allow full access to the Pulp server)

   There are various certificate related settings in this file that can be
   safely ignored for current PulpDist installations. They relate to the use
   of access controlled repositories, which PulpDist doesn't currently support.
   Setting up the AMQP messaging support is also an option, but not required.

#. Update ``/etc/pulpdist/site.conf`` in accordance with the embedded comments.
   Notably:

   * Enter the initial list of system administrators
   * Set the passphrase for encrypted database fields
   * Generate and enter a private Django secret key (see below)

#. Update  ``/etc/httpd/conf.d/pulpdist.conf`` to set the Kerberos domain
   correctly (and, optionally, add a keytab reference for single-sign-on
   support). Note that ``pulpdist-httpd`` makes a number of assumptions that
   are only valid when using Kerberos for authentication - if you want to do
   something else (e.g. use Django's native authentication), install
   ``pulpdist-django`` instead (either directly or an RPM dependency) and
   include ``pulpdist.django_app`` as an installed application in a custom
   Django site definition.

#. Initialise and start the Pulp server. This will start both the MongoDB data
   store as well the Apache web server (note that running Pulp's ``init.d``
   scripts directly doesn't appear to work correctly)::

   $ service pulp-server init
   $ service pulp-server start

#. Update ``/etc/pulp/admin/admin.conf`` to replace ``localhost.localdomain``
   with the fully qualified domain of the server

#. Optionally, set up a separate administrator account for the Pulp server and
   restrict the default admin account to read-only access (currently used via
   the web UI over OAuth) ::

      # Use the default account to add a new administrator
      pulp-admin auth login --username admin
      pulp-admin user create --username ncoghlan --name "Nick Coghlan" --ldap
      pulp-admin role add --role super-users --user ncoghlan

      # Use the new administrator account to restrict the default account
      pulp-admin auth login --username ncoghlan
      pulp-admin role create --role read-only
      pulp-admin permission grant --resource / --role read-only -o read
      pulp-admin role add --role read-only --user admin
      pulp-admin role remove --role super-users --user admin

      # Check the permissions have been updated appropriately
      pulp-admin permission show --resource /

#. Log in to the PulpDist web application as one of the system administrators
   configured in Step 2. Click the "Site Admin" link, then use the Django admin
   UI to add a reference to the colocated Pulp server. The fields are as
   follows:

   * Pulp site: name used in the user interface for this server
   * Hostname: fully qualified hostname for this server (will be checked by SSL)
   * Oauth key: the Pulp OAuth key configured in Step 1
   * Oauth secret: the Pulp OAuth secret configured in Step 1


The following command can be used to generate a fresh Django secret key::

   python -c 'from random import choice; print("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)]))'

.. _`Pulp Installation Guide`: http://pulpproject.org/ug/UGInstallation.html
.. _OAuth authentication: https://fedorahosted.org/pulp/wiki/AuthenticationOAuth#HowTo
.. _LDAP user authentication: https://fedorahosted.org/pulp/wiki/AuthenticationLDAP#ConfigurepulptouseLDAP:


Django Admin CLI
----------------

The command line interface for Django administration of the site is available
as::

   $ sudo python -m pulpdist.manage_site --help

Refer to the `Django documentation`_ for details of what this command supports
(like the default ``manage.py``, ``pulpdist.manage_site`` is a thin
convenience wrapper around ``django-admin``).

.. _Django documentation: https://docs.djangoproject.com/en/1.3/ref/django-admin/#django-admin-py-and-manage-py

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
    api/repos/<server_id>/<repo_id>/importer       # Importer config & status
    api/repos/<server_id>/<repo_id>/distributors   # Assigned distributors
    api/repos/<server_id>/<repo_id>/sync_history   # Past sync operations

    api/content_types                         # All content types on all servers
    api/content_types/<server_id>/            # All content types on server
    api/content_types/<server_id>/<type_id>/  # Specific content type definition

    api/distributors                           # All distributors on all servers
    api/distributors/<server_id>/              # All distributors on server
    api/distributors/<server_id>/<plugin_id>/  # Specific distributor definition

    api/importers                           # All importers on all servers
    api/importers/<server_id>/              # All importers on server
    api/importers/<server_id>/<plugin_id>/  # Specific importer definition
