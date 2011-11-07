"""Form definitions for Pulp UI"""

from django import forms
from .models import PulpServer

class PulpServerForm(forms.ModelForm):
    class Meta:
        model = PulpServer
        widgets = {
            'oauth_key': forms.TextInput,
            'oauth_secret': forms.PasswordInput(render_value=True),
        }
