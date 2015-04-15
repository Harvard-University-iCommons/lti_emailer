from .local import *

# Make tests faster
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
        'TEST_NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    },
    'termtool': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
        'TEST_NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    },
}

"""
Unit tests should be able to run without talking to external services like
redis/elasticache.  Let's disable the caching middleware, and use the db
to store session data.
"""
MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
MIDDLEWARE_CLASSES[MIDDLEWARE_CLASSES.index('cached_auth.Middleware')] = \
    'django.contrib.auth.middleware.AuthenticationMiddleware'
MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

"""
Don't assume we'll have oauth credentials set for us in secure.py, set
them up here instead.
"""
SECURE_SETTINGS.setdefault('lti_oauth_credentials', {}).update({'foo': 'bar'})
if not LTI_OAUTH_CREDENTIALS:
    LTI_OAUTH_CREDENTIALS = {}
LTI_OAUTH_CREDENTIALS.update({'foo': 'bar'})
