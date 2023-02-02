import logging
import json

from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from icommons_common.view_utils import create_json_200_response, create_json_500_response
from lti_school_permissions.decorators import lti_permission_required

from .models import MailingList, CourseSettings


logger = logging.getLogger(__name__)


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
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

        mailing_lists = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(
            canvas_course_id,
            defaults={
                'created_by': logged_in_user_id,
                'modified_by': logged_in_user_id
            }
        )

    except Exception:
        message = "Failed to get_or_create MailingLists with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(mailing_lists)


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['PUT'])
def set_access_level(request, mailing_list_id):
    """
    Sets the access_level for the given mailing_list on the listserv service

    :param request:
    :param mailing_list_id:
    :return: JSON response containing the updated mailing list data
    """
    ACCESS_LEVELS = ('staff', 'members', 'readonly')

    access_level = json.loads(request.body)['access_level']
    if access_level not in ACCESS_LEVELS:
        logger.warn(f"{access_level} not a valid access_level. Mailing list {mailing_list_id} not modified.")
        raise PermissionDenied

    try:
        logged_in_user_id = request.LTI['lis_person_sourcedid']

        mailing_list = MailingList.objects.get(id=mailing_list_id)
        mailing_list.modified_by = logged_in_user_id
        mailing_list.access_level = access_level
        mailing_list.save()

        cache.delete(settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % mailing_list.canvas_course_id)

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


@login_required
@lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
@require_http_methods(['GET', 'PUT'])
def get_or_create_course_settings(request):
    """
    method allows both GET and PUT requests. If GET is used, we will try to get the object
    if the object does not exist, it will be created with default values.
    If put is used, we will try to get the object
    if the object does not exist, it will be created and the put value will be used instead of the default.
    :param request:
    :return: JSON response of the course settings object
    """
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    canvas_course_id = request.LTI['custom_canvas_course_id']

    try:
        (course_settings, created) = CourseSettings.objects.get_or_create(
            canvas_course_id=canvas_course_id)
        if request.method == 'GET' and not created:
            pass  # just return data, don't update/save record with timestamp
        else:
            if request.method == 'PUT':
                always_mail_staff_flag = json.loads(request.body)[
                    'always_mail_staff']
                course_settings.always_mail_staff = always_mail_staff_flag
            course_settings.modified_by = logged_in_user_id
            course_settings.save()
            cache.delete(
                settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % canvas_course_id)
    except Exception:
        message = "Failed to get_or_create CourseSettings for course %s" % canvas_course_id
        logger.exception(message)
        return create_json_500_response(message)

    result = {
        'canvas_course_id': course_settings.canvas_course_id,
        'always_mail_staff': course_settings.always_mail_staff,
    }

    return create_json_200_response(result)
