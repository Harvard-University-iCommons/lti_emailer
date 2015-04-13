import logging
import json

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from ims_lti_py.tool_config import ToolConfig

from icommons_common.decorators import validate_resource_link_id


logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def tool_config(request):
    url = "%s://%s%s" % (request.scheme, request.get_host(), reverse('mailing_list:lti_launch'))
    lti_tool_config = ToolConfig(
        title='Mailing List',
        launch_url=url,
        secure_launch_url=url,
        description="""
            This LTI tool allows teaching staff to administer mailing lists for this course site.
        """
    )

    # this is how to tell Canvas that this tool provides a course navigation link:
    course_nav_params = {
        'enabled': 'true',
        'text': 'Mailing List',
        'default': 'disabled',
        'visibility': 'admins',
    }
    lti_tool_config.set_ext_param('canvas.instructure.com', 'course_navigation', course_nav_params)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml', status=200)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['POST'])
def lti_launch(request):
    logger.debug(
        "mailing_list launched with params: %s",
        json.dumps(request.POST.dict(), indent=4)
    )
    return redirect('mailing_list:index', request.POST['resource_link_id'])


@validate_resource_link_id
@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
def index(request, resource_link_id):
    return render(request, 'mailing_list/index.html', {
        'resource_link_id': resource_link_id,
    })
