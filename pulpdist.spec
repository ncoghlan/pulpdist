# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# -- headers - pulpdist Python package  --------------------------------------
Name:           pulpdist
Summary:        Python library for PulpDist web application and associated Pulp plugins
Version:        0.0.5
Release:        1%{?dist}
Group:          Development/Tools
License:        GPLv2
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:     noarch

BuildRequires: rpm-python
BuildRequires: python2-devel
BuildRequires: python-setuptools

Requires: pulp-admin
Requires: python >= 2.6
Requires: python-oauth2
Requires: python-httplib2
Requires: python-dateutil
Requires: m2crypto
Requires: openssl
Requires: python-ldap

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
Requires: Django-south
Requires: python-django-tables2
Requires:  python-djangorestframework

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
Requires: pulp
Requires: rsync

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

# -- files - meta-packages ----------------------------------------------------------
%files -n %{django_meta}
%files -n %{devel_meta}


# -- changelog ---------------------------------------------------------------

%changelog
* ??? Feb ?? 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.5-1
- Fix Pulp Server form in Django admin interface
- Provide link to Django admin from main site when logged in as a site admin
- "pulpdist.manage_repos" CLI added to the core RPM
- the "is_test_run" plugin option is now called "dry_run_only"

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

