import hashlib
import hmac
import json
import logging
import time
from functools import wraps

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse_lazy

logger = logging.getLogger(__name__)


def authenticate(redirect_url=reverse_lazy('mailgun:auth_error')):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            logger.debug(f'authenticating webhook request content type {request.content_type}')
            if request.content_type == 'application/json':
                payload = json.loads(request.body)
                try:
                    timestamp = payload['signature']['timestamp']
                    token = payload['signature']['token']
                    signature = payload['signature']['signature']
                except KeyError:
                    logger.error(f'no signature found in request: {payload}')
                    return redirect(redirect_url)
            else:
                try:
                    timestamp = request.POST['timestamp']
                    token = request.POST['token']
                    signature = request.POST['signature']
                except KeyError as e:
                    logger.error("Received mailgun callback request with missing auth param %s", e)
                    return redirect(redirect_url)

            time_diff = time.time() - float(timestamp)
            if time_diff >= settings.MAILGUN_CALLBACK_TIMEOUT:
                logger.error("Received stale mailgun callback request, time difference was %d", time_diff)
                return redirect(redirect_url)

            listserv_api_key = settings.LISTSERV_API_KEY
            digest = hmac.new(
                key=listserv_api_key.encode('utf-8'),
                msg=('{}{}'.format(timestamp, token)).encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()

            if signature != digest:
                logger.error("Received invalid mailgun callback request signature %s != digest %s", signature, digest)
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
