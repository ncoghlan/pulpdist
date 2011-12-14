PulpDist Development
====================

PulpDist is written primarily in Python and developed in git on
`Fedora Hosted`_. Issue tracking is handled in Bugzilla_.

_`Fedora Hosted`: http://fedorahosted.org/pulpdist
_`Bugzilla`: https://bugzilla.redhat.com/buglist.cgi?product=PulpDist&bug_status=__open__

Target Platforms
----------------

The code is currently known to work only under Python 2.7 on Fedora. It
should eventually also run under 2.6+ on RHEL and on other \*nix systems.

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
  * django-tables2 (simply HTML display of tabular data)
  * djangorestframework (simple development of rich REST APIs)
  * pulp-admin (used to simplify access to server REST API)

Standard deployment configuration assumes Apache + mod_wsgi deployment,
but alternatives are likely possible.


Setting up a basic devel environment
------------------------------------

First, install the pulp-admin client as described in the `Pulp User Guide`_.

The following set of instructions should then provide a working development
instance of the ``pulpdist`` web application on a Fedora system::

    sudo yum install Django
    sudo yum install python-pip
    sudo yum install Django-south
    sudo yum install python-nose
    sudo yum install python-m2crypto
    sudo yum install python-oauth2
    sudo pip-python install django-tables2
    sudo pip-python install djangorestframework
    sudo pip-python install mock
    sudo pip-python install djangosanetesting

    git clone git://fedorahosted.org/pulpdist.git pulpdist
    cd pulpdist/src/pulpdist
    ./manage.py syncdb
    ./manage.py migrate django_pulpdist
    ./manage.py runserver

Pointing your preferred browser at ``http://localhost:8000/pulpdist``
should then display the web UI. Pulp server definitions can be
entered either through the REST API or else via the Django admin
interface.

_`Pulp User Guide`: http://pulpproject.org/ug/UGInstallation.html


Setting up a devel environment
------------------------------

Running the test suite (from the base directory)::

    make test


