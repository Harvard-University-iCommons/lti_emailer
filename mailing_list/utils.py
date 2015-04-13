import logging
import json

from django.conf import settings

from canvas_sdk.methods import enrollments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.canvas_utils import SessionInactivityExpirationRC

from icommons_common.models import Person
from models import EmailWhitelist

from mailing_list.listserv_clients.mailgun import MailgunClient as ListservClient


SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


logger = logging.getLogger(__name__)


def sync_mailing_lists_with_listserv(mailing_lists):
    for ml in mailing_lists:
        canvas_course_id = ml.canvas_course_id
        unsubscribed = {x.email for x in ml.unsubscribed_set.all()}

        try:
            canvas_enrollments = get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_courses, canvas_course_id)
        except CanvasAPIError:
            logger.exception("Failed to get canvas enrollments for canvas_course_id %s", canvas_course_id)
            raise

        univ_ids = []
        for enrollment in canvas_enrollments:
            try:
                univ_ids.append(enrollment['user']['sis_user_id'])
            except KeyError:
                logger.debug("Found canvas enrollment with missing sis_user_id %s", json.dumps(enrollment, indent=4))
        enrolled_emails = set([p.email_address for p in Person.objects.filter(univ_id__in=univ_ids)])

        mailing_list_emails = enrolled_emails - unsubscribed

        # Only add subscribers to the listserv if:
        # 1. The subscriber is on the whitelist
        # OR
        # 2. Settings tell us to ignore the whitelist
        if not hasattr(settings, 'IGNORE_WHITELIST'):
            mailing_list_emails = mailing_list_emails.intersection({x.email for x in EmailWhitelist.objects.all()})

        listserv_emails = {m['address'] for m in ListservClient().members(ml)}

        ListservClient().add_members(ml, mailing_list_emails - listserv_emails)
        ListservClient().delete_members(ml, listserv_emails - mailing_list_emails)
