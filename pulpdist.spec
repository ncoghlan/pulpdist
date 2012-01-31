# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# For commented out dependencies marked as (PyPI)
# do a manual 'pip install name' without the
# leading 'python-' until they have been packaged
# properly for Fedora/EPEL/etc

# -- headers - pulpdist Python package  --------------------------------------
Name:           pulpdist
Summary:        Python library for PulpDist web application and associated Pulp plugins
Version:        0.0.2
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
# Requires: python-django-tables2 (PyPI)
# Requires:  python-djangorestframework (PyPI)

%description -n %{django_meta}
Additional dependencies needed to actually use the Django app component
provided in the %{name} Python module.


# -- headers - PulpDist Django App on Apache --------------------------------

%package -n %{deploy_package}
Summary:        Basic Django site definition to serve %{name} on Apache

Requires: %{name} = %{version}
Requires: %{django_meta} = %{version}
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
# Requires:  python-setuptools-git (PyPI)

# Testing dependencies
Requires:  python-nose
# Requires:  python-mock (PyPI)
# Requires:  python-djangosanetesting (PyPI)


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
mkdir -p %{buildroot}/etc/%{name}
cp -R etc/%{name}/* %{buildroot}/etc/%{name}
# Logging
mkdir -p %{buildroot}/var/log/%{name}
# Storage for misc files (e.g. Django sqlite3 ORM)
mkdir -p %{buildroot}/var/lib/%{name}
# Storage for static media files (e.g. CSS, JS, images)
mkdir -p %{buildroot}%{httpd_static_media}
# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/%{name}.conf %{buildroot}/etc/httpd/conf.d/
# WSGI Service Hook
mkdir -p %{buildroot}/srv/%{name}
cp srv/%{name}/django.wsgi %{buildroot}/srv/%{name}/django.wsgi

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
chmod -R u=rwX,g=rX,o=rX %{data_dir}
chown -R apache:apache %{data_dir}

# Static files (CSS, JS, images)
pushd src
%{run_manage_site} collectstatic --noinput
popd
chmod -R u=rwX,g=rX,o=rX %{httpd_static_media}
chown -R apache:apache %{httpd_static_media}

# -- files - Main Python package -----------------------------------------------------

%files
%defattr(644,root,root,755)
%doc
# For noarch packages: sitelib
%{python_sitelib}/%{name}/*/
%{python_sitelib}/%{name}/*.py[co]
%{python_sitelib}/%{name}/__init__.py
%attr(755,root,root) %{python_sitelib}/%{name}/manage_site.py

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


# -- changelog ---------------------------------------------------------------

%changelog
* Tue Jan 27 2012 Nick Coghlan <ncoghlan@redhat.com> 0.0.2
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

