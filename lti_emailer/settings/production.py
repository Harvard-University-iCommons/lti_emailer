from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += ('gunicorn',)

GUNICORN_CONFIG = 'gunicorn_prod.py'

SESSION_COOKIE_SECURE = True

# Allow the mailing_list app to allow any user to be added to listserv
IGNORE_WHITELIST = True
