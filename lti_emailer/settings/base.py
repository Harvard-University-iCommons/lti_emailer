"""
Django settings for lti_emailer project.
"""

import os
import re
import logging
from django.urls import reverse_lazy
from dj_secure_settings.loader import load_secure_settings

SECURE_SETTINGS = load_secure_settings()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key', 'changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECURE_SETTINGS.get('enable_debug', False)

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_auth_lti',
    'icommons_common',
    'lti_permissions',
    'icommons_ui',
    'djng',
    'lti_emailer',
    'mailing_list',
    'mailgun'
]

MIDDLEWARE = [
    # NOTE - djng needs to be the first item in this list
    'djng.middleware.AngularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'cached_auth.Middleware',
    'django_auth_lti.middleware_patched.MultiLTILaunchAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django_auth_lti.backends.LTIAuthBackend',
)

LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'lti_emailer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'lti_emailer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASE_ROUTERS = ['icommons_common.routers.CourseSchemaDatabaseRouter']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': SECURE_SETTINGS.get('db_default_name', 'lti_emailer'),
        'USER': SECURE_SETTINGS.get('db_default_user', 'postgres'),
        'PASSWORD': SECURE_SETTINGS.get('db_default_password'),
        'HOST': SECURE_SETTINGS.get('db_default_host', '127.0.0.1'),
        'PORT': SECURE_SETTINGS.get('db_default_port', 5432),  # Default postgres port
    },
    'coursemanager': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': SECURE_SETTINGS.get('db_coursemanager_name'),
        'USER': SECURE_SETTINGS.get('db_coursemanager_user'),
        'PASSWORD': SECURE_SETTINGS.get('db_coursemanager_password'),
        'HOST': SECURE_SETTINGS.get('db_coursemanager_host'),
        'PORT': str(SECURE_SETTINGS.get('db_coursemanager_port')),
        'OPTIONS': {
            'threaded': True,
        },
        'CONN_MAX_AGE': 0,
    }
}

COURSE_SCHEMA_DB_NAME = 'coursemanager'

# Cache
# https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-CACHES

REDIS_HOST = SECURE_SETTINGS.get('redis_host', '127.0.0.1')
REDIS_PORT = SECURE_SETTINGS.get('redis_port', 6379)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "redis://%s:%s/0" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'KEY_PREFIX': 'lti_emailer',  # Provide a unique value for intra-app cache
        # See following for default timeout (5 minutes as of 1.7):
        # https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-CACHES-TIMEOUT
        'TIMEOUT': SECURE_SETTINGS.get('default_cache_timeout_secs', 300),
    },
    'shared': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "redis://%s:%s/0" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'KEY_PREFIX': 'tlt_shared',
        'TIMEOUT': SECURE_SETTINGS.get('default_cache_timeout_secs', 300),
    }
}

# Sessions

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# NOTE: This setting only affects the session cookie, not the expiration of the session
# being stored in the cache.  The session keys will expire according to the value of
# SESSION_COOKIE_AGE, which defaults to 2 weeks when no value is given.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'
# A boolean that specifies whether Django's translation system should be enabled. This provides
# an easy way to turn it off, for performance. If this is set to False, Django will make some
# optimizations so as not to load the translation machinery.
USE_I18N = False

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'http_static'))

# Logging

_DEFAULT_LOG_LEVEL = SECURE_SETTINGS.get('log_level', 'DEBUG')
_LOG_ROOT = SECURE_SETTINGS.get('log_root', '')  # Default to current directory

# Turn off default Django logging
# https://docs.djangoproject.com/en/2.2/topics/logging/#disabling-logging-configuration
LOGGING_CONFIG = None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s\t%(asctime)s.%(msecs)03dZ\t%(name)s:%(lineno)s\t%(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s\t%(name)s:%(lineno)s\t%(message)s',
        }
    },
    # Borrowing some default filters for app loggers
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    # This is the default logger for any apps or libraries that use the logger
    # package, but are not represented in the `loggers` dict below.  A level
    # must be set and handlers defined.  Setting this logger is equivalent to
    # setting and empty string logger in the loggers dict below, but the separation
    # here is a bit more explicit.  See link for more details:
    # https://docs.python.org/2.7/library/logging.config.html#dictionary-schema-details
    'root': {
        'level': logging.WARNING,
        'handlers': ['console', 'app_logfile'],
    },
    'handlers': {
        # Log to a text file that can be rotated by logrotate
        'app_logfile': {
            'level': _DEFAULT_LOG_LEVEL,
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(_LOG_ROOT, 'django-lti_emailer.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': logging.DEBUG,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
    },
    'loggers': {
        # TODO: remove this catch-all handler in favor of app-specific handlers
        '': {
            'handlers': ['console', 'app_logfile'],
            'level': _DEFAULT_LOG_LEVEL,
        },
        'django.request': {
            'handlers': ['console', 'app_logfile'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'propagate': False,
        },
        'py.warnings': {
            'handlers': ['console'],
            'propagate': False,
        },
        'lti_emailer': {
            'level': _DEFAULT_LOG_LEVEL,
            'handlers': ['console', 'app_logfile'],
            'propagate': False,
        },
        'mailgun': {
            'level': _DEFAULT_LOG_LEVEL,
            'handlers': ['console', 'app_logfile'],
            'propagate': False,
        },
        'mailing_list': {
            'level': _DEFAULT_LOG_LEVEL,
            'handlers': ['console', 'app_logfile'],
            'propagate': False,
        },
        'icommons_common': {
           'handlers': ['console', 'app_logfile'],
           'level': _DEFAULT_LOG_LEVEL,
           'propagate': False,
        },
    }
}

# Currently deployed environment
ENV_NAME = SECURE_SETTINGS.get('env_name', 'local')

# Other app specific settings

LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)

CANVAS_URL = SECURE_SETTINGS.get('canvas_url', 'https://canvas.instructure.com')

CANVAS_SDK_SETTINGS = {
    'auth_token': SECURE_SETTINGS.get('canvas_token', None),
    'base_api_url': CANVAS_URL + '/api',
    'max_retries': 3,
    'per_page': 40,
    'session_inactivity_expiration_time_secs': 50,
}

ICOMMONS_COMMON = {
    'ICOMMONS_API_HOST': SECURE_SETTINGS.get('icommons_api_host', None),
    'ICOMMONS_API_USER': SECURE_SETTINGS.get('icommons_api_user', None),
    'ICOMMONS_API_PASS': SECURE_SETTINGS.get('icommons_api_pass', None),
    'CANVAS_API_BASE_URL': CANVAS_URL + '/api/v1',
    'CANVAS_API_HEADERS': {
        'Authorization': 'Bearer ' + SECURE_SETTINGS.get('canvas_token', 'canvas_token_missing_from_config')
    },
}

REPORT_DIR = SECURE_SETTINGS.get('report_dir', BASE_DIR)

LISTSERV_DOMAIN = SECURE_SETTINGS.get('listserv_domain')
LISTSERV_API_URL = SECURE_SETTINGS.get('listserv_api_url')
LISTSERV_API_USER = SECURE_SETTINGS.get('listserv_api_user')
LISTSERV_API_KEY = str(SECURE_SETTINGS.get('listserv_api_key'))

LISTSERV_SECTION_ADDRESS_RE = re.compile("^canvas-(?P<canvas_course_id>\d+)-(?P<section_id>\d+)@%s$" % LISTSERV_DOMAIN)
LISTSERV_COURSE_ADDRESS_RE = re.compile("^canvas-(?P<canvas_course_id>\d+)@%s$" % LISTSERV_DOMAIN)

LISTSERV_SECTION_ADDRESS_FORMAT = "canvas-{canvas_course_id}-{section_id}@%s" % LISTSERV_DOMAIN
LISTSERV_COURSE_ADDRESS_FORMAT = "canvas-{canvas_course_id}@%s" % LISTSERV_DOMAIN

PERMISSION_LTI_EMAILER_VIEW = 'lti_emailer_view'
PERMISSION_LTI_EMAILER_SEND_ALL = 'lti_emailer_send_all'

MAILGUN_CALLBACK_TIMEOUT = 30 * 1000  # 30 seconds

IGNORE_WHITELIST = SECURE_SETTINGS.get('ignore_whitelist', False)

CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID = "mailing_lists_by_canvas_course_id-%s"

CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT = "lti_emailer:message-handled:%s:%s"
CACHE_KEY_MESSAGE_HANDLED_TIMEOUT = 60 * 60 * 8  # 8 hours

NO_REPLY_ADDRESS = SECURE_SETTINGS.get('no_reply_address', 'no-reply@coursemail.harvard.edu')
