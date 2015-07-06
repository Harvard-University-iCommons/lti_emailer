import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from lti_emailer.canvas_api_client import get_enrollments


logger = logging.getLogger(__name__)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
def admin_index(request):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    logger.info("Rendering mailing_list admin_index view for user %s" % logged_in_user_id)
    return render(request, 'mailing_list/admin_index.html', {})


@login_required
@require_http_methods(['GET'])
def learner_index(request):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    logger.info("Rendering mailing_list learner_index view for user %s" % logged_in_user_id)
    return render(request, 'mailing_list/learner_index.html', {})


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
def list_members(request, section_id):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    canvas_course_id = request.LTI.get('custom_canvas_course_id')
    if not logged_in_user_id:
        raise RuntimeError() # TODO - FIXME
    if not canvas_course_id:
        raise RuntimeError() # TODO - FIXME
    logger.info('Rendering mailing_list section_list_details view for user {}, '
                'canvas course {}, section {}'.format(
                    logged_in_user_id, canvas_course_id, section_id))

    enrollments = get_enrollments(canvas_course_id, section_id)
    return render(request, 'mailing_list/list_details.html',
                  {'section_id': section_id, 'enrollments': enrollments})
