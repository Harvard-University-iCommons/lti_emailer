import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseBadRequest
from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required
from icommons_common.auth.lti_decorators import has_course_permission
from icommons_common.canvas_api.helpers import courses as canvas_api_helper_courses

from lti_emailer.canvas_api_client import get_enrollments, get_section, get_course
from mailing_list.models import MailingList


logger = logging.getLogger(__name__)


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@has_course_permission(canvas_api_helper_courses.COURSE_PERMISSION_SEND_MESSAGES_ALL)
@require_http_methods(['GET'])
def admin_index(request):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    canvas_course_id = request.LTI.get('custom_canvas_course_id')

    course_code = get_course(canvas_course_id)['course_code']

    logger.info("Rendering mailing_list admin_index view for user %s"
                % logged_in_user_id)
    return render(request, 'mailing_list/admin_index.html', { 'course_code' : course_code})


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@has_course_permission(canvas_api_helper_courses.COURSE_PERMISSION_SEND_MESSAGES_ALL)
@require_http_methods(['GET'])
def list_members(request, section_id=None):
    canvas_course_id = request.LTI.get('custom_canvas_course_id')

    if not canvas_course_id:
        return HttpResponseBadRequest('Unable to determine canvas course id')

    logger.info(
        'Rendering mailing_list section_list_details view for canvas course {}, section {}'.format(
            canvas_course_id, section_id
        )
    )

    if section_id:
        mailing_list = get_object_or_404(MailingList, canvas_course_id=canvas_course_id, section_id=section_id)
    else:
        mailing_list = get_object_or_404(MailingList, canvas_course_id=canvas_course_id, section_id__isnull=True)

    enrollments = get_enrollments(canvas_course_id, section_id)

    enrollments.sort(key=lambda x: x['sortable_name'])
    section = get_section(canvas_course_id, section_id)

    if not section:
        course_code = get_course(canvas_course_id)['course_code']
        section = {
            'id' : 0,
            'name' : course_code,
        }

    return render(request, 'mailing_list/list_details.html',
                  {'section': section,
                   'enrollments': enrollments})
