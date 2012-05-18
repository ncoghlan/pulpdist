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
"""Model definitions for Pulp UI"""

from django.db import models
from django.db.utils import DatabaseError
from django.conf import settings
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError

from ..core import pulpapi

from .fields import EncryptedCharField

# Create your models here.
class PulpServer(models.Model):
    """Database model for Pulp Server details"""

    pulp_site = models.CharField(max_length=200, null=False,
                                 blank=False, unique=True)

    server_slug = models.SlugField(max_length=200, null=False,
                                   blank=False, unique=True, editable=False)

    hostname = models.CharField(max_length=200, null=False, blank=False)
    # Hardcode for now (not actually used yet)
    port = 443
    scheme = 'https'

    # Use OAuth for access to allow proper auditing in Pulp logs
    # Storage is split so two secrets are needed to retrieve the OAuth keys
    #  - the storage database itself (with the keys in encrypted form)
    #  - the project settings file (with the passphrase for the keys)
    _passphrase_setting = 'PULPAPI_OAUTH_KEY_STORE_PASSPHRASE'
    oauth_key = EncryptedCharField(max_length=200,
                                   passphrase_setting=_passphrase_setting,
                                   null=False, blank=False)
    oauth_secret = EncryptedCharField(max_length=200,
                                      passphrase_setting=_passphrase_setting,
                                      null=False, blank=False)
    del _passphrase_setting

    @property
    def server(self):
        try:
            return self._server
        except AttributeError:
            self._init_server()
        return self._server

    def _init_server(self):
        self._server = pulpapi.PulpServer(self.hostname,
                                          self.oauth_key.encode('utf-8'),
                                          self.oauth_secret.encode('utf-8'))

    def __unicode__(self):
        return "Pulp server: %s(%s)" % (self.pulp_site, self.hostname)

    def clean(self):
        super(PulpServer, self).clean()
        if not self.server_slug:
            slug = slugify(self.pulp_site)
            try:
                model = PulpServer.objects.get(server_slug=slug)
            except self.DoesNotExist:
                self.server_slug = slug
            else:
                msg = "Pulp server ID '%s' already in use for site '%s'"
                raise ValidationError(msg % (slug, model.pulp_site))
        self._init_server()

    def save(self, *args, **kwds):
        if not self.server_slug:
            self.server_slug = slugify(self.pulp_site)
        super(PulpServer, self).save(*args, **kwds)

    def get_repos(self):
        return self.add_slug_seq(self.server.get_repos())

    def get_repo(self, repo_id):
        return self.add_slug(self.server.get_repo(repo_id))

    def get_importer(self, repo_id):
        return self.server.get_importer(repo_id)

    def get_sync_history(self, repo_id, limit=None):
        return self.server.get_sync_history(repo_id, limit)

    def add_slug_seq(self, data):
        for item in data:
            self.add_slug(item)
        return data

    def add_slug(self, data):
        data['server_slug'] = self.server_slug
        return data
        