#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import sys
from setuptools import setup, find_packages

# Generates a single Python package which may be turned
# into multiple distinct RPMs
#   - pulpdist.core
#   - pulpdist.pulp_plugins
#   - pulpdist.django_app
#   - pulpdist.django_site


# There is some 2.7 specific code in the current codebase
# but it's at least *supposed* to run on 2.6
major, minor, micro = sys.version_info[:3]
if major != 2 or minor not in [6, 7]:
    raise Exception('Unsupported version of Python (need 2.6/7, not %s)'
                        % (sys.version_info,))

project_name             = 'pulpdist'
project_url              = 'https://fedorahosted.org/pulpdist/'
project_author           = 'Red Hat, Inc.'
project_maintainer       = 'Nick Coghlan'
project_point_of_contact = 'ncoghlan@redhat.com'
project_description      = 'Pulp based mirroring network'
project_packages         = find_packages()
project_version          = '0.0.1'
project_license          = 'GPLv2+'
project_classifiers      = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Operating System :: POSIX',
        'Topic :: Content Management and Delivery',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Development Status :: 2 - Pre-Alpha',
]
project_requires = [
    # Functional
    'pulp',
    'django-tables2',
    'django-uni-form',
    'djangorestframework',
    # Installation
    'south',
    # Test
    'django-sane-testing',
    'mock'
]
project_setup_requires = [
    'setuptools-git',
]

setup(
    name             = project_name,
    version          = project_version,
    url              = project_url,
    author           = project_author,
    author_email     = project_point_of_contact, 
    maintainer       = project_maintainer,
    maintainer_email = project_point_of_contact,
    description      = project_description,
    license          = project_license,
    classifiers      = project_classifiers,
    install_requires = project_requires,
    setup_requires   = project_setup_requires,
    packages         = project_packages,
    # Data file declarations in MANIFEST.in
    include_package_data = True,
)
