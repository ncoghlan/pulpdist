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

from django.conf import settings
from django.contrib.auth.models import User

DUMMY_USER = settings.DUMMY_AUTH_USER
DUMMY_STAFF = settings.DUMMY_AUTH_STAFF
DUMMY_SUPER = settings.DUMMY_AUTH_SUPER

DUMMY_USERS = [DUMMY_USER, DUMMY_STAFF, DUMMY_SUPER]

class DummyAuthBackend(object):
    """
    Automatically provide normal, staff and super users for testing purposes
    """
    supports_inactive_user = False
    supports_anonymous_user = False
    supports_object_permissions = False

    def authenticate(self, username=None, password=None):
        if username not in DUMMY_USERS:
            return None
        # raise Exception("Checking DUMMY AUTH for {0}".format(username))
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create the dummy user. We leave the password
            # unusable so that the dummy users can't be
            # used with the normal auth mechanisms
            # raise Exception("DUMMY AUTH attempting to create {0}".format(username))
            email = username + "@example.com.invalid"
            user = User.objects.create_user(username, email)
            user.is_staff = (user == DUMMY_STAFF)
            user.is_super = (user == DUMMY_SUPER)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None