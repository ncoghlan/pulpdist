import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulpdist.settings'

try:
    import pulpdist
except ImportError:
    # Development environment, use symlinked version
    import sys
    _this_dir = os.path.dirname(__file__)
    sys.path.append(os.path.join(_this_dir, 'pulpdist_dev'))

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
 
