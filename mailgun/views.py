import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from lti_tool.decorators import lti_launch_required

from mailgun.decorators import authenticate

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@lti_launch_required
@login_required
def auth_error(request):
    return JsonResponse({"error": "Failed to authenticate request."}, status=401)


@csrf_exempt
@authenticate()
@require_http_methods(["POST"])
@lti_launch_required
@login_required
def log_post_data(request):
    """
    This method will log POST data. It is primarily provided so that it can be configured as an endpoint for the
    Mailgun Webhooks to log an event, which would help in monitoring  the various configured  events that are available
    (such as Delivered, Dropped, Bounces, etc). But it could also be used to log any post.
    :param request:
    :return HttpResponse:
    """
    if request.content_type == "application/json":
        payload = json.loads(request.body)
        logger.info(json.dumps(payload["event-data"]))
    else:
        logger.info(json.dumps(request.POST, separators=(",", ": "), sort_keys=True))

    return HttpResponse("Successfully logged post data", status=200)
