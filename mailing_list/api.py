import logging
import json

from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from icommons_common.view_utils import create_json_200_response, create_json_500_response
from lti_permissions.decorators import lti_permission_required

from .models import MailingList


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

        logger.debug('%s' % mailing_lists)

    except Exception:
        message = u"Failed to get_or_create MailingLists with LTI params %s" % json.dumps(request.LTI)
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
    try:
        logged_in_user_id = request.LTI['lis_person_sourcedid']
        access_level = json.loads(request.body)['access_level']

        mailing_list = MailingList.objects.get(id=mailing_list_id)
        mailing_list.modified_by = logged_in_user_id
        mailing_list.date_modified = timezone.now()
        mailing_list.access_level = access_level
        mailing_list.save()

        cache.delete(settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % mailing_list.canvas_course_id)

        result = {
            'id': mailing_list.id,
            'address': mailing_list.address,
            'access_level': access_level
        }
    except Exception:
        message = u"Failed to activate MailingList %s with LTI params %s" % (mailing_list_id, json.dumps(request.LTI))
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(result)
