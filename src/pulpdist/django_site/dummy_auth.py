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
"""DummyAuth backend to provide a default 'admin' user in dev environments"""

import logging

from django.conf import settings
from django.contrib.auth.models import User

DUMMY_USER = settings.DUMMY_AUTH_USER
DUMMY_STAFF = DUMMY_USER + "-admin"
DUMMY_SUPER = DUMMY_USER + "-su"

DUMMY_USERS = [DUMMY_USER, DUMMY_STAFF, DUMMY_SUPER]

_log = logging.getLogger("pulpdist.dummy_auth")

class DummyAuthBackend(object):
    """
    Automatically provide normal, staff and super users for testing purposes
    """
    supports_inactive_user = False
    supports_anonymous_user = False
    supports_object_permissions = False

    def authenticate(self, username=None, password=None):
        _log.debug("Authenticating %s against %s", username, DUMMY_USERS)
        if username not in DUMMY_USERS:
            _log.debug("%s is not a valid dummy user", username)
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create the dummy user. We leave the password
            # unusable so that the dummy users can't be
            # used with the normal auth mechanisms
            # (if DummyAuth *is* enabled, you can just enter
            # any old password and it will accept it)
            email = username + "@example.com.invalid"
            user = User.objects.create_user(username, email)
            user.is_active = True
            user.is_staff = username in (DUMMY_STAFF, DUMMY_SUPER)
            user.is_superuser = username == DUMMY_SUPER
            user.save()
            _log.debug("Created %s dummy user", username)
        _log.debug("Returning %s (Staff=%s, Super=%s)", username, user.is_staff, user.is_superuser)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None