import logging
import json

from datetime import datetime

from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const
from django_auth_lti.verification import has_lti_roles

from icommons_common.view_utils import create_json_200_response, create_json_500_response

from lti_emailer import canvas_api_client
from .models import MailingList


logger = logging.getLogger(__name__)


def _filter_mailing_lists_for_user(canvas_user_id, mailing_lists):
    result = []
    for ml in mailing_lists:
        if ml['access_level'] != MailingList.ACCESS_LEVEL_READONLY:
            enrollments = canvas_api_client.get_enrollments(ml['canvas_course_id'], ml['section_id'])
            user_ids = [enrollment['user']['id'] for enrollment in enrollments]
            if canvas_user_id in user_ids:
                result.append(ml)

    return result


@login_required
@require_http_methods(['GET'])
def lists(request):
    """
    Gets the list of mailing lists for the course in the current session context

    :param request:
    :return: JSON response containing the mailing lists for the course in this session context
    """
    try:
        canvas_course_id = request.LTI['custom_canvas_course_id']
        logged_in_user_id = request.LTI['lis_person_sourcedid']

        mailing_lists = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(
            canvas_course_id,
            defaults={
                'created_by': logged_in_user_id,
                'modified_by': logged_in_user_id
            }
        )

        if not has_lti_roles(request, [
            const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER
        ]):
            # Learners should only see lists which they can post to, so filter the mailing lists
            canvas_user_id = int(request.LTI.get('custom_canvas_user_id'))
            mailing_lists = _filter_mailing_lists_for_user(canvas_user_id, mailing_lists)
    except Exception:
        message = "Failed to get_or_create MailingLists with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(mailing_lists)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['PUT'])
def set_access_level(request, mailing_list_id):
    """
    Sets the access_level for the given mailing_list on the listserv service

    :param request:
    :param mailing_list_id:
    :return: JSON response containing the updated mailing list data
    """
    try:
        logged_in_user_id = request.LTI['lis_person_sourcedid']
        access_level = json.loads(request.body)['access_level']

        mailing_list = MailingList.objects.get(id=mailing_list_id)
        mailing_list.modified_by = logged_in_user_id
        mailing_list.date_modified = datetime.utcnow()
        mailing_list.update_access_level(access_level)

        result = {
            'id': mailing_list.id,
            'address': mailing_list.address,
            'access_level': access_level
        }
    except Exception:
        message = "Failed to activate MailingList %s with LTI params %s" % (mailing_list_id, json.dumps(request.LTI))
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(result)
