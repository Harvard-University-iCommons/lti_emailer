import logging

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
# @authenticate()
@require_http_methods(['POST'])
def log_post_data(request):
    """
    This method will help in logging the POST information. This method is provided as an endpoint for the
    Mailgun Webhooks to log an event, so that we can track the various configured  events that are available
    (such as Delivered, Dropped, Bounces, etc)
    :param request:
    :return HttpResponse:
    """
    # logger.info(" Full mailgun post: %s", request.POST)
    logger.info(" Logging Webhook Post data")

    # Log the event type , time and description
    for key, value in request.POST.iteritems():
        logger.info(" Key= %s, Value =%s", key, value)

    logger.info(" Webhook event type:%s, Recipient:%s, Message-header:%s", request.POST.get('event'),
                request.POST.get('recipient'), request.POST.get('message-headers'))
    return HttpResponse("Successfully logged post data", status=200)
