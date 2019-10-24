import json
import logging

import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from lti import ToolConfig

from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required
from lti_permissions.decorators import lti_permission_required

logger = logging.getLogger(__name__)


def lti_auth_error(request):
    raise PermissionDenied()


@require_http_methods(['GET'])
def tool_config(request):
    url = "https://{}{}".format(request.get_host(), reverse('lti_launch'))
    url = _url(url)

    title = 'Admin Console'
    lti_tool_config = ToolConfig(
        title=title,
        launch_url=url,
        secure_launch_url=url,
        description="This LTI tool provides a suite of tools for administering your Canvas account."
    )

    # this is how to tell Canvas that this tool provides an account navigation link:
    nav_params = {
        'enabled': 'true',
        'text': title,
        'default': 'disabled',
        'visibility': 'admins',
    }
    custom_fields = {'canvas_membership_roles': '$Canvas.membership.roles'}
    lti_tool_config.set_ext_param('canvas.instructure.com', 'custom_fields', custom_fields)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'account_navigation', nav_params)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


def _url(url):
    """
    *** Taken from ATG's django-app-lti repo to fix the issue of resource_link_id being included in the launch url
    *** TLT-3591
    Returns the URL with the resource_link_id parameter removed from the URL, which
    may have been automatically added by the reverse() method. The reverse() method is
    patched by django-auth-lti in applications using the MultiLTI middleware. Since
    some applications may not be using the patched version of reverse(), we must parse the
    URL manually and remove the resource_link_id parameter if present. This will
    prevent any issues upon redirect from the launch.
    """

    parts = urllib.parse.urlparse(url)
    query_dict = urllib.parse.parse_qs(parts.query)
    if 'resource_link_id' in query_dict:
        query_dict.pop('resource_link_id', None)
    new_parts = list(parts)
    new_parts[4] = urllib.parse.urlencode(query_dict)
    return urllib.parse.urlunparse(new_parts)


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['POST'])
@csrf_exempt
def lti_launch(request):
    logger.debug(
        "lti_emailer launched with params: %s",
        json.dumps(request.POST.dict(), indent=4)
    )
    return redirect('mailing_list:admin_index')
