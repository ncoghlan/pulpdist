PulpDist Development
====================

PulpDist is written primarily in Python and developed in git on
`Fedora Hosted`_. Issue tracking is handled in Bugzilla_.

.. _Fedora Hosted: http://fedorahosted.org/pulpdist
.. _Bugzilla: https://bugzilla.redhat.com/buglist.cgi?product=PulpDist&bug_status=__open__


Target Platforms
----------------

The code is currently tested and known to work under Python 2.7 on Fedora and
under Python 2.6 on RHEL6. It should also run under either version of Python on
other \*nix systems (so long as the relevant dependencies are available).

The client and plugins are written to work with the 1.x series of Pulp. Any
errors encountered while using Pulp 1.x should be reported on the bug tracker.

The Pulp 2.x series (due for initial release in July 2012) is not currently
supported.


Build/Test Dependencies
-----------------------

  * setuptools/distribute (packaging)
  * setuptools-git (tito RPM build tool support)
  * tito (RPM build tool)
  * sphinx (the reStructuredText documentation tool)
  * sphinxcontrib-blockdiag (not used yet, but will be eventually)
  * nose (test runner)
  * unittest2 (backport of Python 2.7 unittest module to earlier versions)
  * mock (the Python test library, not the Fedora packaging utility)
  * mock/mockbuild (the Fedora packaging utility)
  * djangosanetesting (web app test runner)
  * parse (date/time checking)


Plugin Dependencies
-------------------

(not necessarily complete)

  * rsync (currently used via CLI, may some day switch to librsync)
  * pulp (of course!)


Web Application Dependencies
----------------------------

(not necessarily complete)

  * Django 1.3+ (built on Class Based Views)
  * Django-south (database migrations)
  * python-m2crypto (OAuth support, including protected config storage)
  * python-oauth2 (OAuth based access to Pulp)
  * django-tables2 (simple HTML display of tabular data)
  * djangorestframework (simple development of rich REST APIs)
  * pulp-admin (used to simplify access to server REST API)

Standard deployment configuration assumes Apache + mod_wsgi + mod_auth_kerb
deployment, but alternatives are likely possible.


Setting up a basic devel environment
------------------------------------

First, install the pulp-admin client as described in the
`Pulp Installation Guide`_.

The following set of instructions should then provide a working development
instance of the ``pulpdist`` web application on a Fedora 16 system::

    $ sudo yum install Django Django-south python-nose python-m2crypto python-oauth2 tito
    $ sudo wget -O /etc/yum.repos.d/fedora-pulpdist.repo http://repos.fedorapeople.org/repos/pulpdist/pulpdist/fedora-pulpdist.repo
    $ sudo yum install python-django-tables2 python-djangorestframework python-mock python-djangosanetesting python-setuptools-git

    $ git clone git://fedorahosted.org/pulpdist.git pulpdist
    $ cd pulpdist/src
    $ python -m pulpdist.manage_site syncdb
    $ python -m pulpdist.manage_site migrate
    $ python -m pulpdist.manage_site runserver

Pointing your preferred browser at ``http://localhost:8000``
should then display the web UI with the dummy authentication scheme enabled.
Pulp server definitions can be entered either through the REST API or else
via the Django admin interface (use ``pulpdist-test-su`` as the login name to
get access to the latter).

_`Pulp Installation Guide`: http://pulpproject.org/ug/UGInstallation.html

.. note:

   These instructions are known to be incomplete. Additional steps are
   needed in order to actually load the plugins into Pulp.


Running the unit tests
----------------------

Running the test suite (from the base directory of the source checkout)::

    $ make test

Some of these test may require a Pulp server running on the local machine with
OAuth enabled. Refer to the `Pulp Installation Guide`_ and
`OAuth authentication`_ for details.

.. _OAuth authentication: https://fedorahosted.org/pulp/wiki/AuthenticationOAuth#HowTo


.. _building-rpms:

Building the PulpDist RPMs
--------------------------

Currently, there are no prebuilt RPMs for PulpDist available. However,creating
them locally is intended to be straightforward::

    $ make rpm

This will create a ``pulpdist`` SRPM, along with the following ``noarch`` RPMs:

* ``pulpdist`` - the core Python package for PulpDist
* ``pulpdist-plugins`` - the custom Pulp plugins for tree synchronisation
* ``pulpdist-django``  - a meta-package that brings in the additional
  dependencies needed to actually run ``pulpdist.django_app``
* ``pulpdist-httpd`` - installs the PulpDist web application, largely
  preconfigured to run under Apache using Kerberos-over-Basic-Auth for
  authentication.
* ``pulpdist-devel`` - a meta-package that isn't currently very useful,
  but will eventually be available in the public repo to make it easy to
  bring in all the dependencies needed to work on PulpDist.

``pulpdist-plugins`` should be installed on all Pulp servers in a PulpDist
network.

``pulpdist-httpd`` can be installed directly to use the standard PulpDist
Django site settings. Alternatively, any RPM-based Django site definitions
that use the PulpDist Django application should depend on
``pulpdist`` and ``pulpdist-django``.
