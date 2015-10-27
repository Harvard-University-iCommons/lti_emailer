#!/usr/bin/env python

import hashlib
import hmac
import json
import time
import uuid

import requests
from django.conf import settings

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
    'sender': 'Integration Test <integrationtest@example.edu>',
    'from': list_address,
    'recipient': list_address,
    'subject': 'blah',
    'body-plain': 'blah blah',
    'To': list_address,
}
post_body.update(generate_signature_dict())

# post it
url = 'https://lti-emailer.dev.tlt.harvard.edu/mailgun/handle_mailing_list_email_route/'
resp = requests.post(url, data=post_body)
resp.raise_for_status()
