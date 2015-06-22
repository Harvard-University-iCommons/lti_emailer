import logging
import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from icommons_common.view_utils import create_json_200_response

from mailgun.decorators import authenticate


logger = logging.getLogger(__name__)


@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
def handle_mailing_list_email_route(request):
    """
    Handles the Mailgun route action when email is sent to a Mailgun mailing list.

    :param request:
    :return:
    """
    logger.info("Handling Mailgun mailing list email route: %s", json.dumps(request.POST.dict()))

    return create_json_200_response({'success': True})
