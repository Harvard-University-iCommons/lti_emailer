import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseBadRequest
from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required

from lti_permissions.decorators import lti_permission_required

from lti_emailer.canvas_api_client import get_enrollments, get_section, get_course
from mailing_list.models import MailingList

from mailing_list.utils import is_course_crosslisted

logger = logging.getLogger(__name__)


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['GET'])
def admin_index(request):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    canvas_course_id = request.LTI.get('custom_canvas_course_id')

    course = get_course(canvas_course_id)

    if course['name']:
        course_name = course['name']
    elif course['course_code']:
        course_name = course['course_code']
    else:
        course_name = canvas_course_id
        
    logger.info(u"Rendering mailing_list admin_index view for user %s",
                logged_in_user_id)
    return render(request, 'mailing_list/admin_index.html', {'course_name': course_name,})


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['GET'])
def list_members(request, section_id=None):
    canvas_course_id = request.LTI.get('custom_canvas_course_id')

    if not canvas_course_id:
        return HttpResponseBadRequest('Unable to determine canvas course id')

    logger.info(
        u'Rendering mailing_list section_list_details view for canvas course %s '
        u'section %s', canvas_course_id, section_id)

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
            'id': 0,
            'name': course_code,
        }

    return render(request, 'mailing_list/list_details.html',
                  {'section': section,
                   'enrollments': enrollments})
