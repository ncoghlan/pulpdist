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
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login, logout
# from django.contrib.auth import logout
import logging

_log = logging.getLogger(__name__)

LOGIN_TEMPLATE = 'pulpdist/login.tmpl'
LOGOUT_TEMPLATE = 'pulpdist/logout.tmpl'

class PulpDistAuthForm(AuthenticationForm):
    allow_local_auth = getattr(settings, "ENABLE_DUMMY_AUTH", False)
    if allow_local_auth:
        dummy_user = settings.DUMMY_AUTH_USER

def login_view(request):
    next_page = request.GET.get("next", settings.LOGIN_REDIRECT_URL)
    _log.debug("Attempting to log in. Next page: %s", next_page)
    return login(request,
                 template_name=LOGIN_TEMPLATE,
                 authentication_form=PulpDistAuthForm)

def logout_view(request):
    _log.debug("Attempting to log out")
    return logout(request, template_name=LOGOUT_TEMPLATE)


class LDAPAuthBackend(RemoteUserBackend):
    def clean_username(self, username):
        _log.debug("Accepted LDAP login: %s", username)
        return username

    def configure_user(self, user):
        name = user.username
        _log.info("Created new LDAP user: %s", name)
        if '@' in name: # We assume LDAP logins map to email addresses...
            email = name.lower()
            _log.debug("Setting email address for %s to %s", name, email)
            user.email = email
            if email in settings.PULPDIST_ADMINS:
                _log.debug("Configuring %s as a site administrator", name)
                user.is_staff = user.is_superuser = True
        user.save()
        return user
