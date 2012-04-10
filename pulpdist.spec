# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# -- headers - pulpdist Python package  --------------------------------------
Name:           pulpdist
Summary:        Python library for PulpDist web application and associated Pulp plugins
Version:        0.0.11
Release:        1%{?dist}
Group:          Development/Tools
License:        GPLv2
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:     noarch

BuildRequires: rpm-python
BuildRequires: python2-devel
BuildRequires: python-setuptools

Requires: pulp-admin >= 0.0.262
Requires: python >= 2.6
Requires: python-oauth2
Requires: python-httplib2
Requires: python-dateutil
Requires: m2crypto
Requires: openssl
Requires: python-ldap
Requires: python-sqlalchemy >= 0.5
Requires: python-argparse

# Note: pulpdist.django_app/site require additional dependencies to execute
#       Refer to the pulpdist-django meta package dependencies listed below.

# Installation dependencies
Requires: python-setuptools

%define deploy_package %{name}-httpd
%define plugin_package %{name}-plugins
%define django_meta %{name}-django
%define devel_meta %{name}-devel

%description
The PulpDist Python package includes all of the Python components needed by
%{deploy_package} and %{plugin_package}.


# -- headers - Django app dependencies metapackage -----------------------

%package -n %{django_meta}
Summary:        Additional dependencies for the PulpDist Django app component

Requires: Django >= 1.3
Requires: Django-south >= 0.7
Requires: python-django-tables2 >= 0.8
Requires:  python-djangorestframework >= 0.3

%description -n %{django_meta}
Additional dependencies needed to actually use the Django app component
provided in the %{name} Python module.


# -- headers - PulpDist Django App on Apache --------------------------------

%package -n %{deploy_package}
Summary:        Basic Django site definition to serve %{name} on Apache

Requires: %{name} = %{version}
Requires: %{django_meta} = %{version}
Requires: policycoreutils-python
Requires: httpd
Requires: mod_ssl
Requires: mod_wsgi
Requires: mod_auth_kerb

%description -n %{deploy_package}
A web frontend for managing and monitoring a network of Pulp servers used
as a private mirroring network. Deploys and serves %{name} as a standalone
Django site on Apache. 


# -- headers - PulpDist plugins for Pulp  -------------------------------------------------

%package -n %{plugin_package}
Summary:        Pulp plugins to support PulpDist mirroring network

Requires: %{name} = %{version}
Requires: pulp >= 0.0.262
Requires: rsync
Requires: hardlink

# Requires: python-parse
# Not yet packaged, use "pip install parse" instead

%description -n %{plugin_package}
The Pulp plugins to be installed on each Pulp server in a PulpDist mirroring network


# -- headers - Development dependencies metapackage -----------------------

%package -n %{devel_meta}
Summary:        Additional dependencies for PulpDist development

Requires: %{django_meta} = %{version}

# RPM creation
Requires: tito
Requires:  python-setuptools-git

# Testing dependencies
Requires:  python-nose
Requires:  python-mock
Requires:  python-djangosanetesting


%description -n %{devel_meta}
Meta-package defining additional dependencies for PulpDist testing and
RPM creation


# -- build -------------------------------------------------------------------

%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd

%define config_dir /etc/%{name}
%define log_dir /var/log/%{name}
%define service_dir /srv/%{name}

%define data_dir /var/lib/%{name}
%define database_file %{data_dir}/djangoORM.db

%define httpd_static_media /var/www/pub/%{name}

%define plugin_src src/%{name}/pulp_plugins
%define plugin_dest /var/lib/pulp/plugins
%define plugin_type_spec types/%{name}.json
%define plugin_importer importers/%{name}_importers
%define plugin_distributor distributors/%{name}_distributors
%define plugin_sync_logs /var/www/pub/%{name}_sync_logs

%install
rm -rf %{buildroot}
# Main Python package
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

# 'Database' file for buildroot (real one is created in post-install)
mkdir -p %{buildroot}%{data_dir}
touch %{buildroot}%{database_file}

# Apache deployment configuration files and directories
mkdir -p %{buildroot}%{config_dir}
cp -R etc/%{name}/* %{buildroot}%{config_dir}
# Logging
mkdir -p %{buildroot}%{log_dir}
# Storage for static media files (e.g. CSS, JS, images)
mkdir -p %{buildroot}%{httpd_static_media}
# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/%{name}.conf %{buildroot}/etc/httpd/conf.d/
# WSGI Service Hook
mkdir -p %{buildroot}%{service_dir}
cp srv/%{name}/django.wsgi %{buildroot}%{service_dir}/django.wsgi

# Pulp plugins
mkdir -p %{buildroot}%{plugin_dest}/types
cp %{plugin_src}/%{plugin_type_spec} %{buildroot}%{plugin_dest}/%{plugin_type_spec}
mkdir -p %{buildroot}%{plugin_dest}/%{plugin_importer}
cp -R %{plugin_src}/%{plugin_importer}/* %{buildroot}%{plugin_dest}/%{plugin_importer}
mkdir -p %{buildroot}%{plugin_dest}/%{plugin_distributor}
cp -R %{plugin_src}/%{plugin_distributor}/* %{buildroot}%{plugin_dest}/%{plugin_distributor}
# Storage for in-progress sync logs
mkdir -p %{buildroot}%{plugin_sync_logs}

%clean
rm -rf %{buildroot}


# -- post-install - Main Python package -----------------------------------------------------

%define run_manage_site %{__python} -m %{name}.manage_site

%post
# Nothing to do

%postun
# Nothing to do?

# -- post-install - Apache deployment -----------------------------------------------------

%post -n %{deploy_package}
# Django ORM
if [ "$1" = "1" ]; then
  %{run_manage_site} syncdb --noinput
fi
%{run_manage_site} migrate
popd
chmod -R u=rwX,g=rX,o=rX %{data_dir} %{log_dir}
chown -R apache:apache %{data_dir} %{log_dir}

# Static files (CSS, JS, images)
pushd src
%{run_manage_site} collectstatic --noinput
popd
chmod -R u=rwX,g=rX,o=rX %{httpd_static_media}
chown -R apache:apache %{httpd_static_media}

# SELinux contexts for Apache runtime access
if selinuxenabled ; then
# Read-only httpd access
    semanage fcontext -a -t httpd_sys_content_t "%{config_dir}(/.*)?"
    restorecon -R %{config_dir}
    semanage fcontext -a -t httpd_sys_content_t "%{service_dir}(/.*)?"
    restorecon -R %{service_dir}

# Read-write httpd access
    semanage fcontext -a -t httpd_sys_rw_content_t "%{log_dir}(/.*)?"
    restorecon -R %{log_dir}
    semanage fcontext -a -t httpd_sys_rw_content_t "%{data_dir}(/.*)?"
    restorecon -R %{data_dir}
fi

%postun -n %{deploy_package}
if selinuxenabled ; then
    semanage fcontext -d "%{config_dir}(/.*)?"
    semanage fcontext -d "%{service_dir}(/.*)?"
    semanage fcontext -d "%{log_dir}(/.*)?"
    semanage fcontext -d "%{data_dir}(/.*)?"
fi

# -- files - Main Python package -----------------------------------------------------

%files
%defattr(644,root,root,755)
%doc
# For noarch packages: sitelib
%{python_sitelib}/%{name}

# -- files - Apache deployment ----------------------------------------------------------

%files -n %{deploy_package}
%defattr(-,root,root,-)
%doc
%config(noreplace) /etc/httpd/conf.d/%{name}.conf
%defattr(644,apache,apache,755)
%attr(750, apache, apache) /srv/%{name}/django.wsgi
%ghost %{database_file}
%{httpd_static_media}
/var/log/%{name}/
%config(noreplace) /etc/%{name}/site.conf

# -- files - Pulp plugins ----------------------------------------------------------
%files -n %{plugin_package}
%defattr(644,apache,apache,755)
%{plugin_dest}/%{plugin_type_spec}
%{plugin_dest}/%{plugin_importer}/
%{plugin_dest}/%{plugin_distributor}/
%{plugin_sync_logs}

# -- files - meta-packages ----------------------------------------------------------
%files -n %{django_meta}
%files -n %{devel_meta}


# -- changelog ---------------------------------------------------------------

%changelog
* ??? ??? ?? 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.11-1
- BZ#799203 (continued): 3 sync log files are now preserved: <repo_id>.log
  (latest sync attempt), <repo_id>.log.prev (previous sync attempt) and
  <repo_id>.log.bak (latest successful sync attempt).
- BZ#794547: pulpdist.manage_repos now supports the cron_sync command
- BZ#794546: the output of the manage_repos status command has been reformatted
  and now includes details of the current synchronisation status
- BZ#758936 (continued): repo sync history in web UI now displays sync result
- BZ#786678: Include sync status details in repository table in web UI
- BZ#811053: rsync invocation no longer relies on the system shell
- BZ#799203 (continued): link to sync logs from Web UI is now also correct for
  Pulp servers that are not colocated with the Web UI instance
- BZ#758936 (continued): main repo page in web UI now included latest sync
  result, as well as links to log files.

* Thu Mar 29 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.10-1
- "exclude_from_listing" entries that conflict with the listing_pattern are
  now correctly ignored when creating a repo config from a mirror config
- use line-buffered IO when sync log output is requested by passing in a
  filesystem path
- BZ#799203 (continued): due to the potential file size (and associated
  problems with storage in MongoDB and the amount of data included when
  retrieving sync history from the server), the sync log is now stored solely
  on the Pulp server filesystem. The repo management CLI had been updated to
  derive the sync log URL from the Pulp server host name and the repository
  identifier.
- BZ#799201: the sync history details now includes plugin_type and
  plugin_version information

* Tue Mar 27 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.9-2
- Actually include the code changes intended for 0.0.9
- Omit trailing slash from directory aliases in pulpdist-site Apache config

* Tue Mar 27 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.9-1
- BZ#802627: For an old remote daemon, the "--old-d" option is still needed for
  directory listing operations. It should only be omitted for the actual sync
  operations

* Mon Mar 26 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.8-1
- BZ#806740: Added "latest_link" attribute to remote tree configurations to
  correctly handle cases where the listing_prefix doesn't match the desired
  name for the link (the link name is now *never* derived from the prefix)

* Thu Mar 22 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.7-3
- Fix some Python 2.6 incompatibilities that crept into the source
- Move sync log directory ownership to the plugins RPM (where it belongs)

* Thu Mar 22 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.7-2
- Correctly identify the sync log directory as part of the httpd deployment

* Thu Mar 22 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.7-1
- BZ#795212: the manage_repos client now uses a new site configuration format
- site configuration data is saved to the server as the "pulpdist-meta" repo
- if no configuration file is provided, the manage_repos init and validate
  commands will use the data in the "puldist-meta" repo if it is available
- the --repo filtering option is now applied at the individual subcommand level
  rather than at the manage_repos invocation level
- when the site configuration data is available, manage_repos now supports
  filtering by the local site and mirror names and the remote tree, source and
  server, in addition to filtering directly by repository identifier
- the --ignoremeta option is now available to tell the command line to treat
  the Pulp server as if it was simply a collection of raw trees
- the old configuration format is no longer supported, use a site configuration
  file that defines only RAW_TREES instead
- the two phases of versioned and snapshots syncs are now consistently referred
  to as the "listing" and "sync" phases. Several configuration settings have
  been renamed accordingly.
- BZ#802627: rsync commands now use the "--no-implied-dirs" option when
  communicating with an old remote daemon
- the "sync_log" CLI command has been shortened to "log"
- the "sync_stats" CLI command has been shortened to "stats"
- BZ#799204: the manage_repos CLI now provides a -V/--version option
- BZ#799205: the web UI footer now displays a more accurate version number
- Fixed a race condition with tests waiting for the rsync server to start
- BZ#799203: in-progress sync logs are now published via https as flat files

* Fri Feb 17 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.6-1
- Created pulpdist.cli subpackage for Management CLI support code
- Renamed previous "list" command to "info"
- Added new "list" command that just prints the repo id and name
- Added "status" command to print repo sync status
- Renamed manage_repos --file option to --config
- New manage_repos --repo option to limit the repos affected by a command
- manage_repos host selection is now a --host option (defaulting to local FQDN)
- New manage_repos --force option to automatically answer 'yes' to prompts
- "sync" and "init" commands now prompt for each repo by default
- manage_repos now uses argparse subcommand support (much better help output)
- added "enable" command to allow syncs on a repo ("--dryrun" for dry run only)
- added "disable" command to prevent syncs on a repo
- added "history" command to display full sync history
- added "sync_log" command to display most recent sync log output
- added "sync_stats" command to display most recent sync statistics
- fixed NameError in importer plugin error handling
- fixed rsync stat collection for large trees
- fixed rsync stat collection for old remote daemons

* Wed Feb 15 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.5-1
- Fix Pulp Server form in Django admin interface
- Provide link to Django admin from main site when logged in as a site admin
- "pulpdist.manage_repos" CLI added to the core RPM
- The "is_test_run" plugin option is now called "dry_run_only"
- Dry runs now append "_DRY_RUN" to their status result
- The "snapshot_tree" plugin now correctly supports the "dry_run_only" option
- All plugins now support an "enabled" option (defaulting to False), and
  SYNC_DISABLED is a possible status result for a sync request
- The "versioned_tree" and "snapshot_tree" plugins now support a
  "delete_old_dirs" to remove local directories that are no longer present
  on the remote server
- The "versioned_tree" and "snapshot_tree" plugins now ensure upstream
  directories and symlinks to directories are correctly reproduced locally
- The manage_repos script now performs client side config validation
- The manage_repos init command also reinitialises existing repositories
- The regex for rsync filter validation now allows character classes
- Various fixes to the web UI to support display of non-trivial repos

* Wed Feb 08 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.4-3
- Set correct permissions on logging directory in pulpdist-httpd

* Tue Feb 07 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.4-2
- Convert PyPI dependencies to real dependencies (these will be published
  soon in a pulpdist repo at repos.fedorapeople.org)

* Tue Feb 07 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.4-1
- Correctly configure permissions for site administrators
- Default to Kerberos authentication in pulpdist-httpd
- Better handling of web server based authentication

* Tue Jan 31 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.3-1
- Support deployment under SELinux in pulpdist-httpd

* Tue Jan 31 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.2-2
- All post-install operations moved to pulpdist-httpd
- Post install operations actually work as intended
- DJANGO_RPM_ROOT envvar is no more
- Django dependencies moved to separate meta-package
- Development dependencies moved to separate meta-package

* Fri Jan 27 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.1-3
- Don't require things that aren't actually needed (ncoghlan@redhat.com)
- Start repo management script (ncoghlan@redhat.com)

* Wed Jan 11 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.1-2
- initial packaging as pulpdist

