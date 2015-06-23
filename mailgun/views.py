import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def auth_error(request):
    return JsonResponse({'error': 'Failed to authenticate request.'}, status=401)
