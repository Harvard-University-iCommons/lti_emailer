#!/usr/bin/env python

import hashlib
import hmac
import json
import time
import uuid

import requests
from django.conf import settings

try:
    settings.NO_REPLY_ADDRESS
except ImportError:
    # make sure the project root is in sys.path
    import os, sys
    sys.path.insert(0, os.path.normpath(
                           os.path.join(os.path.abspath(__file__), '..', '..', '..')))

def generate_signature_dict():
    timestamp = str(time.time())
    token = str(uuid.uuid4())
    signature = hmac.new(
        key=settings.LISTSERV_API_KEY,
        msg='{}{}'.format(timestamp, token),
        digestmod=hashlib.sha256
    ).hexdigest()
    return {
        'timestamp': timestamp,
        'token': token,
        'signature': signature
    }

# prep the post body
list_address = 'canvas-6760-2069@mg.dev.tlt.harvard.edu'
post_body = {
    'sender': 'integrationtest@example.edu',
    'recipient': list_address,
    'from': 'Integration Test <integrationtest@example.edu>',
    'subject': 'blah',
    'body-plain': 'blah blah',
    'attachment-count': 1,
    'To': list_address,
}
post_body.update(generate_signature_dict())

# figure out which server to post to
env_name = settings.ENV_NAME
if env_name not in ('dev', 'qa', 'stage'):
    env_name = 'dev'

# post it
url = 'https://lti-emailer.%s.tlt.harvard.edu/mailgun/handle_mailing_list_email_route/' % env_name
resp = requests.post(url, data=post_body)

# we're expecting a 400 client error, since we sent a malformed POST.  if we
# didn't get that, squawk about it.
if resp.status_code != 400:
    resp.raise_for_status()

# at this point, check splunk for 'Attachment "missing from POST"'
