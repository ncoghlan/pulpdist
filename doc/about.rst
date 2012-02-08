PulpDist Development
====================

PulpDist is written primarily in Python and developed in git on
`Fedora Hosted`_. Issue tracking is handled in Bugzilla_.

_`Fedora Hosted`: http://fedorahosted.org/pulpdist
_`Bugzilla`: https://bugzilla.redhat.com/buglist.cgi?product=PulpDist&bug_status=__open__


Target Platforms
----------------

The code is currently tested known to work under Python 2.7 on Fedora and under
Python 2.6 on RHEL6. It should also run under either version of Python on
other \*nix systems (so long as the relevant dependencies are available).


Build/Test Dependencies
-----------------------

  * setuptools/distribute (packaging)
  * setuptools-git (tito RPM build tool support)
  * tito (RPM build tool)
  * sphinx (documentation)
  * sphinxcontrib-blockdiag (not used yet, but will be eventually)
  * nose (test runner)
  * mock (the Python test library, not the Fedora packaging utility)
  * djangosanetesting (web app test runner)


Plugin Dependencies
-------------------

(not necessarily complete)

  * rsync (currently used via CLI, may some day switch to librsync)
  * pulp (of course!)


Web Application Dependencies
----------------------------

(not necessarily complete)

  * Django 1.3+ (build on Class Based Views)
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

    $ sudo yum install Django
    $ sudo yum install Django-south
    $ sudo yum install python-nose
    $ sudo yum install python-m2crypto
    $ sudo yum install python-oauth2
    $ sudo wget -O /etc/yum.repos.d/fedora-pulpdist.repo http://repos.fedorapeople.org/repos/pulpdist/pulpdist/fedora-pulpdist.repo
    $ sudo yum install python-django-tables2
    $ sudo yum install python-djangorestframework
    $ sudo yum install python-mock
    $ sudo yum install python-djangosanetesting

    git clone git://fedorahosted.org/pulpdist.git pulpdist
    cd pulpdist/src/pulpdist
    ./manage.py syncdb
    ./manage.py migrate django_pulpdist
    ./manage.py runserver

Pointing your preferred browser at ``http://localhost:8000/pulpdist``
should then display the web UI. Pulp server definitions can be
entered either through the REST API or else via the Django admin
interface.

(Once an initial public RPM release is available in the Fedora People repo then
the above will be simplified to just installing and removing the ``pulpdist``
RPM in order to download all the relevant dependencies)

_`Pulp Installation Guide`: http://pulpproject.org/ug/UGInstallation.html


Running the unit tests
----------------------

Running the test suite (from the base directory)::

    make test

Some of these test may require a Pulp server running on the local machine with
OAuth enabled. Refer to the `Pulp Installation Guide`_ and
`OAuth authentication`_ for details.

.. _OAuth authentication: https://fedorahosted.org/pulp/wiki/AuthenticationOAuth#HowTo