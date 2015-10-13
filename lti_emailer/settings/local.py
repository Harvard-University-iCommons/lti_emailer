from .base import *
from logging.config import dictConfig

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += ('debug_toolbar', 'sslserver')
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

# For Django Debug Toolbar:
INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

dictConfig(LOGGING)


SELENIUM_CONFIG = {
    'selenium_username': SECURE_SETTINGS.get('selenium_user'),
    'selenium_password': SECURE_SETTINGS.get('selenium_password'),
    'selenium_grid_url': SECURE_SETTINGS.get('selenium_grid_url'),
    'base_url': 'https://canvas.icommons.harvard.edu',
    'run_locally': True
}
