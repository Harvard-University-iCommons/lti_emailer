import logging
import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from mailgun.decorators import authenticate

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def auth_error(request):
    return JsonResponse({'error': 'Failed to authenticate request.'}, status=401)


@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
def log_post_data(request):
    """
    This method will help in logging POST data. This method is provided as an endpoint for the
    Mailgun Webhooks to log an event, so that we can monitor the various configured  events that are available
    (such as Delivered, Dropped, Bounces, etc)
    :param request:
    :return HttpResponse:
    """
    logger.info(u'[MAILGUN EVENT] %s', json.dumps(request.POST, indent=4, sort_keys=True))
    return HttpResponse("Successfully logged post data", status=200)
