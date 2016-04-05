#!/usr/bin/env python

import copy
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

# NOTE: this list contains only test accounts, and should be configured as
#       world sendable
list_address = 'canvas-206-3824@mg.dev.tlt.harvard.edu'

# prep the base post body, which has no body params at all
base_post = {
    'sender': 'Integration Test <integrationtest@example.edu>',
    'from': settings.NO_REPLY_ADDRESS,
    'recipient': list_address,
    'subject': 'blah',
    'To': list_address,
}
base_post.update(generate_signature_dict())

# generate the 4 "empty body cases"
bodies = [
    {},
    {'body-html': '', 'body-plain': ''},
    {'body-html': ''},
    {'body-plain': ''},
]
posts = []
for body in bodies:
    post = copy.deepcopy(base_post)
    post.update(body)
    posts.append(post)

# figure out which server to post to
env_name = settings.ENV_NAME
if env_name not in ('dev', 'qa', 'stage'):
    env_name = 'dev'

# do the posts 
url = 'https://lti-emailer.%s.tlt.harvard.edu/mailgun/handle_mailing_list_email_route/' % env_name
for post in posts:
    resp = requests.post(url, data=post)

    # we should get a 200 back indicating the mail has been accepted
    resp.raise_for_status()

# at this point, check the inbox of tlttest53@gmail.com for 4 emails with
# empty bodies
