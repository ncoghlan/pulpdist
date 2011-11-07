from django.template import Library
from django.templatetags.static import PrefixNode
from django.conf import settings

from .. import views

register = Library()

@register.simple_tag
def pulpdist_static_prefix():
    """
    Returns the string contained in the setting PULPDIST_STATIC_PREFIX.

    If not defined, defaults the Django admin styling
    """
    prefix = getattr(settings, "PULPDIST_STATIC_PREFIX", None)
    if not prefix:
        prefix = settings.STATIC_URL + "pulpdist/"
    return prefix

# Default subdirectories (templates are not obliged to use these)
@register.simple_tag
def pulpdist_image_dir():
    """Default directory for images"""
    return pulpdist_static_prefix() + "img/"

@register.simple_tag
def pulpdist_style_dir():
    """Default directory for stylesheets"""
    return pulpdist_static_prefix() + "css/"

@register.simple_tag
def pulpdist_script_dir():
    """Default directory for scripts"""
    return pulpdist_static_prefix() + "js/"

@register.simple_tag
def pulpdist_version():
    """Version number"""
    return "0.1a0"
