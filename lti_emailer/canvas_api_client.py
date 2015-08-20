"""
Utility methods for working with canvas_python_sdk which add a caching layer to the Canvas API calls.

TODO: Incorporate this caching layer into canvas_python_sdk. Punting on this for now to limit collateral concerns.
"""
import logging
import json

from django.conf import settings
from django.core.cache import cache

from canvas_sdk.methods import enrollments, sections, courses
from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.canvas_api.helpers import (
    courses as canvas_api_helper_courses,
    roles as canvas_api_helper_roles
)


logger = logging.getLogger(__name__)

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)
TEACHING_STAFF_ENROLLMENT_TYPES = ['TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment']
USER_ATTRIBUTES_TO_COPY = [u'email', u'name', u'sortable_name']


def get_enrollments(canvas_course_id, section_id):
    users = get_users_in_course(canvas_course_id)
    enrollments = []
    for user in users:
        for enrollment in user['enrollments']:
            if enrollment['course_section_id'] == section_id:
                _copy_user_attributes_to_enrollment(user, enrollment)
                enrollments.append(enrollment)
    return enrollments


def get_name_for_email(canvas_course_id, address):
    users = get_users_in_course(canvas_course_id)
    names_by_email = {u['email']: u['name'] for u in users}
    return names_by_email.get(address, '')


def get_section(canvas_course_id, section_id):
    sections = get_sections(canvas_course_id)
    section_id = int(section_id)
    for section in sections:
        if section['id'] == section_id:
            return section
    return None


def get_sections(canvas_course_id):
    cache_key = settings.CACHE_KEY_CANVAS_SECTIONS_BY_CANVAS_COURSE_ID % canvas_course_id
    result = cache.get(cache_key)
    if not result:
        try:
            result = get_all_list_data(SDK_CONTEXT, sections.list_course_sections, canvas_course_id)
        except CanvasAPIError:
            logger.exception("Failed to get canvas sections for canvas_course_id %s", canvas_course_id)
            raise
        cache.set(cache_key, result)
    return result


def get_teaching_staff_enrollments(canvas_course_id):
    account_id = canvas_api_helper_courses.get_course(canvas_course_id)['account_id']
    users = get_users_in_course(canvas_course_id)
    enrollments = []
    for user in users:
        for enrollment in user['enrollments']:
            if enrollment['type'] in _get_authorized_teaching_staff_enrollment_types(account_id):
                _copy_user_attributes_to_enrollment(user, enrollment)
                enrollments.append(enrollment)
    return enrollments


def get_users_in_course(canvas_course_id):
    cache_key = settings.CACHE_KEY_USERS_BY_CANVAS_COURSE_ID % canvas_course_id
    result = cache.get(cache_key)
    if not result:
        try:
            result = get_all_list_data(
                SDK_CONTEXT,
                courses.list_users_in_course_users,
                canvas_course_id,
                ['email', 'enrollments']
            )
        except CanvasAPIError:
            logger.exception(
                "Failed to get users for canvas_course_id %s",
                canvas_course_id
            )
            raise
        cache.set(cache_key, result)
    return result


def _copy_user_attributes_to_enrollment(user, enrollment):
    enrollment.update({a: user[a] for a in USER_ATTRIBUTES_TO_COPY})


def _get_authorized_teaching_staff_enrollment_types(account_id):
    return [
        role_name
        for role_name in TEACHING_STAFF_ENROLLMENT_TYPES
        if canvas_api_helper_roles.has_permission(
            role_name, account_id, canvas_api_helper_courses.COURSE_PERMISSION_SEND_MESSAGES_ALL
        )
    ]
