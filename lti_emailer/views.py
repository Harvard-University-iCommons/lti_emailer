import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lti.contrib.django import DjangoToolProvider

from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required

from lti_permissions.decorators import lti_permission_required


logger = logging.getLogger(__name__)


def lti_auth_error(request):
    raise PermissionDenied()


@require_http_methods(['GET'])
def tool_config(request):
    env = settings.ENV_NAME if hasattr(settings, 'ENV_NAME') else ''
    url = "%s://%s%s" % (request.scheme, request.get_host(),
                         reverse('lti_launch', exclude_resource_link_id=True))
    title = 'Course Emailer'
    if env and env != 'prod':
        title += ' ' + env
    lti_tool_config = ToolConfig(
        title=title,
        launch_url=url,
        secure_launch_url=url,
        description="This LTI tool allows email functionality for this course site."
    )

    # this is how to tell Canvas that this tool provides a course navigation link:
    course_nav_params = {
        'enabled': 'true',
        'text': title,
        'default': 'disabled',
        'visibility': 'admins',
    }
    custom_fields = {'canvas_membership_roles': '$Canvas.membership.roles'}
    lti_tool_config.set_ext_param('canvas.instructure.com', 'custom_fields', custom_fields)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'course_navigation', course_nav_params)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['POST'])
@csrf_exempt
def lti_launch(request):
    logger.debug(
        u"lti_emailer launched with params: %s",
        json.dumps(request.POST.dict(), indent=4)
    )
    return redirect('mailing_list:admin_index')
