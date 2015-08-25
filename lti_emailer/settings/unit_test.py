from .base import *

# Make tests faster

DATABASE_ROUTERS = []

del DATABASES['termtool']

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    },
}
