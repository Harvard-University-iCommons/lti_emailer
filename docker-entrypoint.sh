#!/bin/sh

python manage.py migrate                  # Apply database migrations
python manage.py collectstatic --noinput  # Collect static files

# Start Gunicorn processes
echo Starting Gunicorn.
exec gunicorn -c lti_emailer/settings/gunicorn.conf.py lti_emailer.wsgi:application
