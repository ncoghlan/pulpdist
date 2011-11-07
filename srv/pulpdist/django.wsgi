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

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulpdist.settings'

try:
    import pulpdist
except ImportError:
    # Development environment, use symlinked version
    import sys
    _this_dir = os.path.dirname(__file__)
    sys.path.append(os.path.join(_this_dir, 'pulpdist_dev'))

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
 
