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
