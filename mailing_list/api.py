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

        ml, _ = MailingList.objects.get_or_create(
            canvas_course_id=canvas_course_id,
            section_id=None,
            defaults={
                'active': False,
                'created_by': logged_in_user_id,
                'modified_by': logged_in_user_id
            }
        )

        result = [{
            'id': ml.id,
            'address': ml.address,
            'active': ml.active
        }]
    except Exception:
        message = "Failed to get_or_create MailingList with LTI params %s" % json.dumps(request.session['LTI_LAUNCH'])
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(result)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['PUT'])
@validate_resource_link_id
def set_active(request, mailing_list_id, resource_link_id):
    try:
        logged_in_user_id = request.session['LTI_LAUNCH']['lis_person_sourcedid']
        active = json.loads(request.body)['active']

        mailing_list = MailingList.objects.get(id=mailing_list_id)
        mailing_list.active = active
        mailing_list.modified_by = logged_in_user_id
        mailing_list.date_modified = datetime.utcnow()
        mailing_list.save()

        result = {
            'id': mailing_list.id,
            'address': mailing_list.address,
            'active': mailing_list.active
        }
    except Exception:
        message = "Failed to activate MailingList %s with LTI params %s" % (
            mailing_list_id,
            json.dumps(request.session['LTI_LAUNCH'])
        )
        logger.exception(message)
        return create_json_500_response(message)

    return create_json_200_response(result)
