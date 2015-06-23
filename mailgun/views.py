import logging
import json

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def auth_error(request):
    return HttpResponse(
        json.dumps({'error': 'Failed to authenticate request.'}),
        status=406,
        content_type='application/json'
    )
