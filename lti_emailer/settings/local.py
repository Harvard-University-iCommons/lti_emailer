from .base import *

import sys
import oracledb
oracledb.version = "8.3.0"
sys.modules["cx_Oracle"] = oracledb

from logging.config import dictConfig

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += ['debug_toolbar', 'django_extensions']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# For Django Debug Toolbar:
INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

LOGGING['handlers']['default'] = {
    'level': DEBUG,
    'class': 'logging.StreamHandler',
    'formatter': 'verbose',
    'filters': ['require_debug_true'],
}
dictConfig(LOGGING)

# REST API info needed for selenium_common
ICOMMONS_REST_API_TOKEN = SECURE_SETTINGS.get('icommons_rest_api_token')
ICOMMONS_REST_API_HOST = SECURE_SETTINGS.get('icommons_rest_api_host')

# Allows the REST API passthrough to successfully negotiate an SSL session
# with an unverified certificate, e.g. the one that ships with django-sslserver
# Default to False, but if testing locally, set to True
ICOMMONS_REST_API_SKIP_CERT_VERIFICATION = SECURE_SETTINGS.get(
            'icommons_rest_api_skip_cert_verification', False)

SELENIUM_CONFIG = {
    'canvas_base_url': SECURE_SETTINGS.get('canvas_url'),
    'emailer_course_id':'27',
    'emailer_tool_id': '141',
    'emailer_tool_relative_url': 'courses/27/external_tools/',
    'icommons_rest_api': {
        'base_path': 'api/course/v2'
    },
    'run_locally': SECURE_SETTINGS.get('selenium_run_locally', False),
    'selenium_grid_url': SECURE_SETTINGS.get('selenium_grid_url'),
    'selenium_password': SECURE_SETTINGS.get('selenium_password'),
    'selenium_username': SECURE_SETTINGS.get('selenium_user'),
    'use_htmlrunner': SECURE_SETTINGS.get('selenium_use_htmlrunner', True),
}
