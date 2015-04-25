import logging

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django_auth_lti.decorators import lti_role_required
from django_auth_lti import const


logger = logging.getLogger(__name__)


@login_required
@lti_role_required([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
@require_http_methods(['GET'])
def index(request):
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    logger.debug("Rendering mailing_list index view for user %s" % logged_in_user_id)
    return render(request, 'mailing_list/index.html', {})
