import logging

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const

from icommons_common.decorators import validate_resource_link_id


logger = logging.getLogger(__name__)


@validate_resource_link_id
@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
def admin_index(request, resource_link_id):
    logged_in_user_id = request.session['LTI_LAUNCH']['lis_person_sourcedid']
    logger.info("Rendering mailing_list admin_index view for user %s" % logged_in_user_id)
    return render(request, 'mailing_list/admin_index.html', {
        'resource_link_id': resource_link_id,
    })


@validate_resource_link_id
@login_required
@require_http_methods(['GET'])
def learner_index(request, resource_link_id):
    logged_in_user_id = request.session['LTI_LAUNCH']['lis_person_sourcedid']
    logger.info("Rendering mailing_list learner_index view for user %s" % logged_in_user_id)
    return render(request, 'mailing_list/learner_index.html', {
        'resource_link_id': resource_link_id,
    })
