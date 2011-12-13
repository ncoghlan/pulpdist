# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PulpServer'
        db.create_table('django_app_pulpserver', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pulp_site', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
            ('server_slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=200, db_index=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('oauth_key', self.gf('pulpdist.django_app.fields.EncryptedCharField')('PULPAPI_OAUTH_KEY_STORE_PASSPHRASE', 200, null=False, blank=False)),
            ('oauth_secret', self.gf('pulpdist.django_app.fields.EncryptedCharField')('PULPAPI_OAUTH_KEY_STORE_PASSPHRASE', 200, null=False, blank=False)),
        ))
        db.send_create_signal('django_app', ['PulpServer'])


    def backwards(self, orm):
        
        # Deleting model 'PulpServer'
        db.delete_table('django_app_pulpserver')


    models = {
        'django_app.pulpserver': {
            'Meta': {'object_name': 'PulpServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'oauth_key': ('pulpdist.django_app.fields.EncryptedCharField', ["'PULPAPI_OAUTH_KEY_STORE_PASSPHRASE'", '200'], {'null': 'False', 'blank': 'False'}),
            'oauth_secret': ('pulpdist.django_app.fields.EncryptedCharField', ["'PULPAPI_OAUTH_KEY_STORE_PASSPHRASE'", '200'], {'null': 'False', 'blank': 'False'}),
            'pulp_site': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'server_slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'})
        }
    }

    complete_apps = ['django_app']
