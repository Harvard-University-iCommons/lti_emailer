"""
Utility methods for working with canvas_python_sdk which add a caching layer to the Canvas API calls.

TODO: Incorporate this caching layer into canvas_python_sdk. Punting on this for now to limit collateral concerns.
"""
import logging

from django.conf import settings
from django.core.cache import caches

from canvas_sdk.methods import (
    accounts,
    communication_channels)
from canvas_sdk.methods.users import list_users_in_account

from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError

from canvas_sdk.client import RequestContext
from canvas_api.helpers import (
    courses as canvas_api_helper_courses,
    sections as canvas_api_helper_sections)

from lti_school_permissions.verification import is_allowed


cache = caches['shared']
logger = logging.getLogger(__name__)

CACHE_KEY_COMM_CHANNELS_BY_CANVAS_USER_ID = "comm-channels-by-canvas-user-id_%s"
CACHE_KEY_USER_IN_ACCOUNT_BY_SEARCH_TERM = "user-in-account-{}-by-search-term-{}"
SDK_CONTEXT = RequestContext(**settings.CANVAS_SDK_SETTINGS)
TEACHING_STAFF_ENROLLMENT_TYPES = ['TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment']
USER_ATTRIBUTES_TO_COPY = ['email', 'name', 'sortable_name']


def get_course(canvas_course_id):
    return canvas_api_helper_courses.get_course(canvas_course_id)


def get_courses_for_account_in_term(account_id, enrollment_term_id,
                                    include_sections=False):
    kwargs = {
        'account_id': account_id,
        'enrollment_term_id': enrollment_term_id,
    }
    if include_sections:
        kwargs['include'] = 'sections'

    try:
        result = get_all_list_data(SDK_CONTEXT, accounts.list_active_courses_in_account, **kwargs)
    except CanvasAPIError:
        logger.error('Unable to get courses for account {}, term {}'.format(account_id, enrollment_term_id))
        raise
    return result


def get_enrollments(canvas_course_id, section_id=None):
    """
    Get the enrollments for a section if a section id is provided.
    Otherwise get all enrollents for the course.
    :param canvas_course_id:
    :param section_id:
    :return enrollments list:
    """
    users = get_users_in_course(canvas_course_id)
    enrollments = []
    for user in users:
        for enrollment in user['enrollments']:
            if section_id:
                if enrollment['course_section_id'] == int(section_id):
                    _copy_user_attributes_to_enrollment(user, enrollment)
                    enrollments.append(enrollment)
            else:
                # if the user has any enrollment in the course
                # we add them to the list and then stop (break)
                # on to the next user.
                _copy_user_attributes_to_enrollment(user, enrollment)
                enrollments.append(enrollment)
                break

    return enrollments


def _filter_student_view_enrollments(enrollments):
    # Filter "Test Student" out of enrollments, "Test Student" is added via the "View as student" feature
    return [x for x in enrollments if x['type'] != 'StudentViewEnrollment']

def get_name_for_email(canvas_course_id, address):
    users = get_users_in_course(canvas_course_id)
    names_by_email = {u['email']: u['name'] for u in users}
    return names_by_email.get(address, '')


def get_section(canvas_course_id, section_id):
    if section_id:
        section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
        return section
    return None


def get_sections(canvas_course_id, fetch_enrollments=True):
    return canvas_api_helper_sections.get_sections(canvas_course_id, fetch_enrollments=fetch_enrollments)


def get_teaching_staff_enrollments(canvas_course_id):
    users = get_users_in_course(canvas_course_id)
    enrollments = []
    roles_allowed = {}
    for user in users:
        for enrollment in user['enrollments']:
            role = enrollment['role']
            if role not in roles_allowed:
                roles_allowed[enrollment['role']] = is_allowed(
                    [role],
                    settings.PERMISSION_LTI_EMAILER_SEND_ALL,
                    canvas_course_id
                )
            if roles_allowed[role]:
                _copy_user_attributes_to_enrollment(user, enrollment)
                enrollments.append(enrollment)
    return enrollments


def get_users_in_course(canvas_course_id):
    try:
        return canvas_api_helper_courses.get_users_in_course(canvas_course_id)
    except:
        logger.exception('failure in canvas_api.helpers.courses.get_users_in_course(): canvas_course_id {}'.format(canvas_course_id))
        raise


def _copy_user_attributes_to_enrollment(user, enrollment):
    enrollment.update({a: user[a] for a in USER_ATTRIBUTES_TO_COPY})


def get_alternate_emails_for_user_email(email_address):
    if not email_address or not email_address.strip():
        return []

    users = _get_users_by_email(email_address)
    users = [u for u in users if u.get('email') == email_address]
    if len(users) == 0:
        logger.error('Looking up alternate mailing list users for {}: '
                     'this address does not match any '
                     'users.'.format(email_address))
        return []

    logger.debug('Looking up alternate mailing list users for {}: '
                 'this address matches the following user(s). User list: '
                 '{}'.format(email_address, users))

    all_comm_channels = list()
    for user in users:
        user_comm_channels = _list_user_comm_channels(user.get('id'))
        all_comm_channels += user_comm_channels if user_comm_channels else []
        logger.debug('Communication channels for user {}: '
                     '{}'.format(user.get('id'), user_comm_channels))

    active_emails = [cc.get('address') for cc in all_comm_channels
                     if cc.get('type') == 'email'
                     and cc.get('workflow_state') == 'active'
                     and cc.get('address')]
    active_emails_deduped = list(set(active_emails))
    logger.debug('Active Canvas email communication channels for sender {}: '
                 '{}'.format(email_address, active_emails_deduped))

    return active_emails_deduped


def _get_users_by_email(email_address, account_id=None, use_cache=True):
    if not email_address or not email_address.strip():
        return []

    if account_id is None:
        account_id = '1'  # account ID for root account in Canvas
    cache_key = CACHE_KEY_USER_IN_ACCOUNT_BY_SEARCH_TERM.format(account_id,
                                                                email_address)
    result = cache.get(cache_key) if use_cache else None
    if not result:
        kwargs = {'search_term': email_address, 'include': 'email'}
        try:
            result = get_all_list_data(
                SDK_CONTEXT,
                list_users_in_account,
                account_id,
                **kwargs)
        except CanvasAPIError:
            logger.error('Unable to lookup users in account {} for email '
                         'address {}'.format(account_id, email_address))
            raise
        logger.debug('Canvas user search results for account {} with search '
                     'term {}: {}'.format(account_id, email_address, result))
        if use_cache:
            cache.set(cache_key, result)
    return result


def _list_user_comm_channels(user_id, use_cache=False):
    """
    Note: we don't want to cache by default because we want to immediately
    pick up changes in user communication channels if they change them, e.g.
    if they're notified they need to update their communication channels and
    they attempt to email a list immediately afterwards, we want to pick up
    that change. Caching can still be done at the level of the mailgun route
    handler event trigger.
    """
    if not user_id:
        return []

    cache_key = CACHE_KEY_COMM_CHANNELS_BY_CANVAS_USER_ID % user_id
    result = cache.get(cache_key) if use_cache else None
    if not result:
        kwargs = {'user_id': user_id}
        try:
            result = get_all_list_data(
                SDK_CONTEXT,
                communication_channels.list_user_communication_channels,
                **kwargs)
        except CanvasAPIError:
            logger.error('Unable to get communication channels for '
                         'Canvas user {}'.format(user_id))
            raise
        logger.debug('Canvas communication channel results for user {}: '
                     '{}'.format(user_id, result))
        if use_cache:
            cache.set(cache_key, result)
    return result
