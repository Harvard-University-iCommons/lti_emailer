import hashlib
import hmac

from functools import wraps

from django.conf import settings
from django.utils.decorators import available_attrs
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy


def authenticate(redirect_url=reverse_lazy('mailgun:auth_error')):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            timestamp = request.POST.get('timestamp')
            token = request.POST.get('token')
            signature = request.POST.get('signature')

            digest = hmac.new(
                key=settings.LISTSERV_API_KEY,
                msg='{}{}'.format(timestamp, token),
                digestmod=hashlib.sha256
            ).hexdigest()

            if signature == digest:
                return view_func(request, *args, **kwargs)

            return redirect(redirect_url)
        return _wrapped_view
    return decorator
