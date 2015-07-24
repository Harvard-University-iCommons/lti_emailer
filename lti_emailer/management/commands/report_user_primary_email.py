import logging
import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from icommons_common.models import Term, CourseInstance

from canvas_sdk.utils import get_all_list_data
from canvas_sdk.methods.courses import list_users_in_course_users
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import Person


SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
        Creates a report of Canvas users enrolled in any course in the given term who have changed their primary email
        address from their default SIS email address.
    """

    def add_arguments(self, parser):
        parser.add_argument('term_id', nargs=1, type=int)

    def handle(self, *args, **options):
        term_id = options['term_id'][0]
        try:
            term = Term.objects.get(term_id=term_id)
        except Term.DoesNotExist:
            raise CommandError('Invalid term_id %d provided.' % term_id)
        logger.info("Creating Canvas user primary email report for term_id %d...", term_id)

        report_data = {}
        for ci in CourseInstance.objects.filter(term=term):
            if ci.canvas_course_id:
                logger.info("Retrieving users for canvas_course_id %d", ci.canvas_course_id)
                users = {}
                try:
                    users_with_email = get_all_list_data(
                        SDK_CONTEXT,
                        list_users_in_course_users,
                        ci.canvas_course_id,
                        'email'
                    )
                    for user in users_with_email:
                        user_id = user['sis_user_id']
                        if user_id not in users:
                            users[user_id] = {'email': user['email'], 'roles': []}

                    users_with_enrollments = get_all_list_data(
                        SDK_CONTEXT,
                        list_users_in_course_users,
                        ci.canvas_course_id,
                        'enrollments'
                    )
                    for user in users_with_enrollments:
                        users[user['sis_user_id']]['roles'].extend(
                            [enrollment['role'] for enrollment in user['enrollments']]
                        )
                except CanvasAPIError:
                    logger.exception("Failed to retrieve users for canvas_course_id %d", ci.canvas_course_id)
                    continue

                for p in Person.objects.filter(univ_id__in=users.keys()):
                    user = users[p.univ_id]
                    if p.email_address != user['email']:
                        for role in user['roles']:
                            if role not in report_data:
                                report_data[role] = []
                            report_data[role].append([role, p.univ_id, user['email']])

        report_path = os.path.join(settings.REPORT_DIR, 'report_user_primary_email.csv')
        with open(report_path, 'wb') as f:
            writer = csv.writer(f, dialect='excel')
            writer.writerow(['Role', 'SIS Email', 'Canvas Email'])
            for role, rows in report_data.iteritems():
                writer.writerows(rows)

        logger.info("User primary email report complete for term_id %d at %s", term_id, report_path)
