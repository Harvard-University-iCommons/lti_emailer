import logging
import json

from urlparse import urlparse

from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const
from django_auth_lti.verification import has_lti_role

from ims_lti_py.tool_config import ToolConfig

from canvas_sdk.methods import external_tools

from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.view_utils import create_json_500_response


logger = logging.getLogger(__name__)

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


def _get_external_tool_id(request):
    """
    Parses the external_tool id from the LTI launch request
    :param request:
    :return: The external_tool id for the given LTI launch request
    """
    return urlparse(request.META.get('HTTP_REFERER')).path.split('/')[-1]


def lti_auth_error(request):
    raise PermissionDenied


@require_http_methods(['GET'])
def tool_config(request):
    env = settings.ENV_NAME if hasattr(settings, 'ENV_NAME') else ''
    url = "%s://%s%s" % (request.scheme, request.get_host(), reverse('lti_launch'))
    lti_tool_config = ToolConfig(
        title="Course Emailer %s" % env,
        launch_url=url,
        secure_launch_url=url,
        description="This LTI tool allows email functionality for this course site."
    )

    # this is how to tell Canvas that this tool provides a course navigation link:
    course_nav_params = {
        'enabled': 'true',
        'text': "Course Emailer %s" % env,
        'default': 'disabled',
        'visibility': 'members',
    }
    lti_tool_config.set_ext_param('canvas.instructure.com', 'course_navigation', course_nav_params)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml', status=200)


@login_required
@lti_role_required([
    const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER, const.LEARNER
])
@require_http_methods(['POST'])
@csrf_exempt
def lti_launch(request):
    logger.debug(
        "lti_emailer launched with params: %s",
        json.dumps(request.POST.dict(), indent=4)
    )

    # external_tool_id = _get_external_tool_id(request)
    # canvas_course_id = request.session['LTI_LAUNCH']['custom_canvas_course_id']
    # tool_config = external_tools.get_single_external_tool_courses(SDK_CONTEXT, canvas_course_id, external_tool_id).json()
    # print json.dumps(tool_config)
    # if tool_config['course_navigation']['visibility'] == 'admins':
    #     tool_config['course_navigation']['visibility'] = 'members'
    # else:
    #     tool_config['course_navigation']['visibility'] = 'admins'
    # external_tools.edit_external_tool_courses(SDK_CONTEXT, canvas_course_id, external_tool_id, payload=tool_config)
    # print json.dumps(tool_config)

    view = 'mailing_list'
    if has_lti_role(request, const.LEARNER):
        view += ":learner_index"
    else:
        view += ":admin_index"

    return redirect(view, request.POST['resource_link_id'])
