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
"""Authentication helpers for PulpDist Web UI"""

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login, logout
# from django.contrib.auth import logout
import logging

_log = logging.getLogger(__name__)

LOGIN_TEMPLATE = 'pulpdist/login.tmpl'
LOGOUT_TEMPLATE = 'pulpdist/logout.tmpl'

class PulpDistAuthForm(AuthenticationForm):
    allow_local_auth = settings.ENABLE_DUMMY_AUTH
    if allow_local_auth:
        dummy_user = settings.DUMMY_AUTH_USER

def login_view(request):
    next_page = request.GET.get("next", settings.LOGIN_REDIRECT_URL)
    _log.info("Attempting to log in. Next page: %s", next_page)
    return login(request,
                 template_name=LOGIN_TEMPLATE,
                 authentication_form=PulpDistAuthForm)

def logout_view(request):
    _log.info("Attempting to log out!")
    return logout(request, template_name=LOGOUT_TEMPLATE)

