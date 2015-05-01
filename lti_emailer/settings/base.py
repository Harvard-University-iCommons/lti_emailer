"""
Django settings for lti_emailer project.

Generated by 'django-admin startproject' using Django 1.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from django.core.urlresolvers import reverse_lazy

from .secure import SECURE_SETTINGS


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key', 'changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECURE_SETTINGS.get('enable_debug', False)

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

# These addresses will receive emails about certain errors
ADMINS = ()

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'icommons_common',
    'icommons_ui',
    'djangular',
    'lti_emailer',
    'mailing_list',
    'gunicorn',
    'huey.djhuey'
)

MIDDLEWARE_CLASSES = (
    'djangular.middleware.DjangularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'cached_auth.Middleware',
    'django_auth_lti.middleware.LTIAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

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
        },
    },
]

WSGI_APPLICATION = 'lti_emailer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASE_APPS_MAPPING = {
    'icommons_common': 'termtool',
    'auth': 'default',
    'contenttypes': 'default',
    'sessions': 'default',
    'mailing_list': 'default'
}

DATABASE_MIGRATION_WHITELIST = ['default']

DATABASE_ROUTERS = ['lti_emailer.routers.DatabaseAppsRouter']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': SECURE_SETTINGS.get('db_default_name', 'lti_emailer'),
        'USER': SECURE_SETTINGS.get('db_default_user', 'postgres'),
        'PASSWORD': SECURE_SETTINGS.get('db_default_password'),
        'HOST': SECURE_SETTINGS.get('db_default_host', '127.0.0.1'),
        'PORT': SECURE_SETTINGS.get('db_default_port', 5432),  # Default postgres port
    },
    'termtool': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': SECURE_SETTINGS.get('db_termtool_name'),
        'USER': SECURE_SETTINGS.get('db_termtool_user'),
        'PASSWORD': SECURE_SETTINGS.get('db_termtool_password'),
        'HOST': SECURE_SETTINGS.get('db_termtool_host'),
        'PORT': str(SECURE_SETTINGS.get('db_termtool_port')),
        'OPTIONS': {
            'threaded': True,
        },
        'CONN_MAX_AGE': 0,
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/lti_emailer/static/'

STATIC_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'http_static'))

REDIS_HOST = SECURE_SETTINGS.get('redis_host', '127.0.0.1')
REDIS_PORT = SECURE_SETTINGS.get('redis_port', 6379)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "%s:%s" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'TIMEOUT': 60 * 20  # 20 minutes
    },
}

# Provide a unique value for sharing cache among Django projects
KEY_PREFIX = 'lti_emailer'

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Django defaults to False (as of 1.7)
SESSION_COOKIE_SECURE = SECURE_SETTINGS.get('use_secure_cookies', False)

LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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

LISTSERV_DOMAIN = SECURE_SETTINGS.get('listserv_domain')
LISTSERV_API_URL = SECURE_SETTINGS.get('listserv_api_url')
LISTSERV_API_USER = SECURE_SETTINGS.get('listserv_api_user')
LISTSERV_API_KEY = SECURE_SETTINGS.get('listserv_api_key')
LISTSERV_ADDRESS_FORMAT = "canvas-{canvas_course_id}-{section_id}@%s" % LISTSERV_DOMAIN
LISTSERV_PERIODIC_SYNC_CRONTAB = SECURE_SETTINGS.get('listserv_periodic_sync_crontab', {'minute': '0'})

CACHE_KEY_CANVAS_SECTIONS_BY_CANVAS_COURSE_ID = "canvas_sections_by_canvas_course_id-%s"
CACHE_KEY_CANVAS_ENROLLMENTS_BY_CANVAS_SECTION_ID = "canvas_enrollments_by_canvas_section_id-%s"
CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID = "mailing_lists_by_canvas_course_id-%s"

HUEY = {
    'backend': 'huey.backends.redis_backend',
    'connection': {'host': REDIS_HOST, 'port': REDIS_PORT},
    'consumer_options': {'workers': 4},  # probably needs tweaking
    'name': 'mailing list management',
}

_DEFAULT_LOG_LEVEL = SECURE_SETTINGS.get('log_level', 'DEBUG')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(module)s %(message)s'
        }
    },
    # Borrowing some default filters for app loggers
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        # Log to a text file that can be rotated by logrotate
        'app_logfile': {
            'level': _DEFAULT_LOG_LEVEL,
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(SECURE_SETTINGS.get('log_root', ''), 'lti_emailer.log'),
            'formatter': 'verbose',
        },
        'huey_logfile': {
            'level': _DEFAULT_LOG_LEVEL,
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(SECURE_SETTINGS.get('log_root', ''), 'huey-lti_emailer.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': _DEFAULT_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'logfile'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': True,
        },
        'django.request': {
            'handlers': ['logfile'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': True,
        },
        'huey': {
            'handlers': ['huey_logfile'],
            'level': _DEFAULT_LOG_LEVEL,
        },
        'mailing_list': {
            'handlers': ['console', 'logfile'],
            'level': _DEFAULT_LOG_LEVEL,
        }
    }
}
