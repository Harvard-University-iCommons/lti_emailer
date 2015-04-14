import logging
import json

from datetime import datetime

from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from icommons_common.decorators import validate_resource_link_id
from icommons_common.view_utils import create_json_200_response, create_json_500_response

from .models import MailingList


logger = logging.getLogger(__name__)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
@validate_resource_link_id
def lists(request, resource_link_id):
    try:
        canvas_course_id = request.session['LTI_LAUNCH']['custom_canvas_course_id']
        logged_in_user_id = request.session['LTI_LAUNCH']['lis_person_sourcedid']

        mailing_lists = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(
            canvas_course_id,
            defaults={
                'created_by': logged_in_user_id,
                'modified_by': logged_in_user_id
            }
        )
    except Exception:
        message = "Failed to get_or_create MailingLists with LTI params %s" % json.dumps(request.session['LTI_LAUNCH'])
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(mailing_lists)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['PUT'])
@validate_resource_link_id
def set_access_level(request, mailing_list_id, resource_link_id):
    try:
        logged_in_user_id = request.session['LTI_LAUNCH']['lis_person_sourcedid']
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
        message = "Failed to activate MailingList %s with LTI params %s" % (
            mailing_list_id,
            json.dumps(request.session['LTI_LAUNCH'])
        )
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(result)
