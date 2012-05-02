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
# Django settings for example pulpdist project.
import os
import tempfile
import logging
from ConfigParser import RawConfigParser, NoOptionError, NoSectionError

# Site specific settings (other than those stored in the database)
CONFIG_ROOT = '/etc/pulpdist/'

SITE_CONFIG_FILE = CONFIG_ROOT + 'site.conf'
SITE_CONFIG = RawConfigParser()

VAR_RELPATH = 'var/lib/pulpdist/'
LOG_RELPATH = 'var/log/pulpdist/'

_sentinel = object()
def _read_option(meth, section, option, default=_sentinel):
    try:
        return meth(section, option)
    except (NoSectionError, NoOptionError):
        if default is not _sentinel:
            return default
        raise

if SITE_CONFIG.read(SITE_CONFIG_FILE):
    # Use deployed settings
    DEBUG = _read_option(SITE_CONFIG.getboolean, 'devel', 'debug_pages', False)
    ENABLE_DUMMY_AUTH = _read_option(SITE_CONFIG.getboolean, 'devel', 'allow_test_users', False)
    PULPAPI_OAUTH_KEY_STORE_PASSPHRASE = SITE_CONFIG.get('database', 'passphrase')
    SECRET_KEY = SITE_CONFIG.get('django', 'secret_key')
    PULPDIST_ADMINS = dict(SITE_CONFIG.items('admins'))
    ADMINS = tuple((email, name) for (name, email) in PULPDIST_ADMINS.iteritems())
    VAR_ROOT = '/' + VAR_RELPATH
    LOG_ROOT = '/' + LOG_RELPATH
else:
    # Use development settings
    DEBUG = True
    ENABLE_DUMMY_AUTH = True
    PULPAPI_OAUTH_KEY_STORE_PASSPHRASE = "better than plaintext oauth key storage!"
    SECRET_KEY = '9@m7g_zn=+gx&g1-a&eyuhs6j+om_&m)uj(n8p4(zj=eu61*eo'
    ADMINS = (
        ('Nick Coghlan', 'ncoghlan@redhat.com'),
    )
    PULPDIST_ADMINS = dict((email, name) for (name, email) in ADMINS)
    # This file is src/pulpdist/django_site/settings.py in Git, set VAR_ROOT accordingly
    import os.path
    _this_dir = os.path.dirname(__file__)
    _checkout_root = os.path.abspath(
                         os.path.normpath(
                             os.path.join(_this_dir, '../../..')))
    VAR_ROOT = os.path.join(_checkout_root, VAR_RELPATH)
    LOG_ROOT = os.path.join(_checkout_root, LOG_RELPATH)

if ENABLE_DUMMY_AUTH:
    DUMMY_AUTH_USER = 'pulpdist-test'

TEMPLATE_DEBUG = DEBUG
MANAGERS = ADMINS

THEME_DIR = VAR_ROOT + 'templates'

DB_NAME = VAR_ROOT + 'djangoORM.db'
TEST_DB_NAME = os.path.join(tempfile.gettempdir(), VAR_RELPATH)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_NAME,                 # path to database file with sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        # 'TEST_NAME': TEST_DB_NAME,       # Enable if in-memory test DB starts causing problems
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/var/www/pub/pulpdist'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Account login page when user details are not provided
LOGIN_URL = '/pulpdist/login'
LOGIN_REDIRECT_URL = '/pulpdist'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'pulpdist.django_app.auth.LDAPAuthBackend',
)

if ENABLE_DUMMY_AUTH:
    AUTHENTICATION_BACKENDS += (
        'pulpdist.django_site.dummy_auth.DummyAuthBackend',
    )

ROOT_URLCONF = 'pulpdist.django_site.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    THEME_DIR,
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
    "pulpdist.django_app.util.app_context"
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'south',
    'djangorestframework',
    'django_tables2',
    'pulpdist.django_app',
)

# Logging config:
#   - attempts to email site admins for 500 errors
#   - INFO+ django messages to LOG_DIR/django.log
#   - all pulp messages to LOG_DIR/pulp.log
#   - all pulpdist app messages to LOG_DIR/pulpdist.log
#   - DEBUG+ (if DEBUG set) or INFO+ (otherwise) to console

LOG_PATH_DJANGO = os.path.join(LOG_ROOT, "django.log")
LOG_PATH_PULP = os.path.join(LOG_ROOT, "pulp.log")
LOG_PATH_PULPDIST = os.path.join(LOG_ROOT, "pulpdist.log")
LOG_PATH_DEBUG = os.path.join(LOG_ROOT, "debug.log")
LOG_PATH_ERROR = os.path.join(LOG_ROOT, "error.log")

def _debug_logger(path):
    return {
        'level':  'DEBUG',
        'class':  'logging.handlers.RotatingFileHandler',
        'filename': path,
        'maxBytes' : 1024*1024,
        'backupCount' : 5,
        'formatter': 'simple'
    }

def _error_logger(path):
    config = _debug_logger(path)
    config['level'] = 'ERROR'
    return config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'console': {
            'level':  'DEBUG' if DEBUG else 'INFO',
            'class':  'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'django_log': _debug_logger(LOG_PATH_DJANGO),
        'pulp_log': _debug_logger(LOG_PATH_PULP),
        'pulpdist_log': _debug_logger(LOG_PATH_PULPDIST),
        'debug_log': _debug_logger(LOG_PATH_DEBUG),
        'error_log': _error_logger(LOG_PATH_ERROR),
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['debug_log', 'error_log', 'django_log'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'pulp': {
            'handlers': ['debug_log', 'error_log', 'pulp_log'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'pulpdist': {
            'handlers': ['debug_log', 'error_log', 'pulpdist_log'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
