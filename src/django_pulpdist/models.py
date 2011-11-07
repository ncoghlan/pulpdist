"""Model definitions for Pulp UI"""

from django.db import models
from django.db.utils import DatabaseError
from django.conf import settings
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError

import pulpapi

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
    _passphrase_setting = 'PULPUI_OAUTH_KEY_STORE_PASSPHRASE'
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
        repos = self.server.get_repos()
        for repo in repos:
            repo['server_slug'] = self.server_slug
        return repos

    def get_repo(self, repo_id):
        repo = self.server.get_repo(repo_id)
        repo['server_slug'] = self.server_slug
        return repo
