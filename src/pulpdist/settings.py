# Django settings for pulpweb project.
import os
import tempfile
from ConfigParser import RawConfigParser

# The RPM spec file sets this variable when needed so
# Django management commands like 'collectstatic'
# will respect the build root when creating the RPM
_RPM_ROOT = os.environ.get('DJANGO_RPM_ROOT', '/')

# Site specific settings (other than those stored in the database)
CONFIG_ROOT = _RPM_ROOT + '/etc/pulpdist/'

SITE_CONFIG_FILE = CONFIG_ROOT + 'site.conf'
SITE_CONFIG = RawConfigParser()

VAR_RELPATH = 'var/lib/pulpdist/'

if SITE_CONFIG.read(SITE_CONFIG_FILE):
    # Use deployed settings
    DEBUG = SITE_CONFIG.has_section('debug')
    PULPUI_OAUTH_KEY_STORE_PASSPHRASE = SITE_CONFIG.get('db_config', 'passphrase')
    ADMINS = tuple(SITE_CONFIG.items('admins'))
    VAR_ROOT = os.path.join(_RPM_ROOT, VAR_RELPATH)
else:
    # Use development settings
    DEBUG = True
    PULPUI_OAUTH_KEY_STORE_PASSPHRASE = "better than plaintext oauth key storage!"
    ADMINS = (
        ('Nick Coghlan', 'ncoghlan@redhat.com'),
    )
    # This file is src/pulpdist/settings.py in Git, set VAR_ROOT accordingly
    import os.path
    _this_dir = os.path.dirname(__file__)
    VAR_ROOT = os.path.abspath(
                  os.path.normpath(
                     os.path.join(_this_dir, '../..', VAR_RELPATH)))

TEMPLATE_DEBUG = DEBUG
MANAGERS = ADMINS

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

TEST_RUNNER = "djangosanetesting.testrunner.DstNoseTestSuiteRunner"
DST_RUN_SOUTH_MIGRATIONS = False
NOSE_ARGS = ['--nologcapture']

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
STATIC_ROOT = _RPM_ROOT + '/var/www/pub/pulpdist'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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

# Make this unique, and don't share it with anybody.
SECRET_KEY = '9@m7g_zn=+gx&g1-a&eyuhs6j+om_&m)uj(n8p4(zj=eu61*eo'

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
)

ROOT_URLCONF = 'pulpdist.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    VAR_ROOT + "templates",
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
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
    'django_pulpdist',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'pulp': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_pulpdist': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'pulpdist': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
