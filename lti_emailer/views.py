import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ims_lti_py.tool_config import ToolConfig

from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required

from icommons_common.auth.lti_decorators import has_account_permission
from icommons_common.canvas_api.helpers import accounts as canvas_helpers_accounts


logger = logging.getLogger(__name__)


def lti_auth_error(request):
    raise PermissionDenied()


@require_http_methods(['GET'])
def tool_config(request):
    env = settings.ENV_NAME if hasattr(settings, 'ENV_NAME') else ''
    url = "%s://%s%s" % (request.scheme, request.get_host(),
                         reverse('lti_launch', exclude_resource_link_id=True))
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
        'visibility': 'admins',
    }
    lti_tool_config.set_ext_param(
        'canvas.instructure.com', 'course_navigation', course_nav_params)
    lti_tool_config.set_ext_param(
        'canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@has_account_permission(canvas_helpers_accounts.ACCOUNT_PERMISSION_SEND_MESSAGES_ALL)
@require_http_methods(['POST'])
@csrf_exempt
def lti_launch(request):
    logger.debug(
        "lti_emailer launched with params: %s",
        json.dumps(request.POST.dict(), indent=4)
    )
    return redirect('mailing_list:admin_index')
