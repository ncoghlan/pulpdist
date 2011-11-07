"""Admin configuration for Pulp UI"""

from django.contrib import admin
from django import forms

from .models import PulpServer
from .fields import EncryptedCharField

class PulpServerAdmin(admin.ModelAdmin):
    prepopulated_fields = {'server_slug' : ['pulp_site']}
    formfield_overrides = {
        # EncryptedCharField: {'widget': forms.PasswordInput(render_value=False)},
    }
    
admin.site.register(PulpServer, PulpServerAdmin)
