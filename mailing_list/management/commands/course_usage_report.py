import argparse
import logging
from operator import itemgetter

from django.core.management.base import BaseCommand, CommandError

import csv

from lti_emailer.canvas_api_client import get_courses_for_account_in_term
from mailing_list.models import MailingList
from canvas_sdk.exceptions import CanvasAPIError

OUTPUT_FIELDS = ['canvas_course_id']

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate CSV report for Course Emailer list of classes that have used Course Emailer for specified Academic Year'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', required=True,
                            help='Canvas account id (e.g. 29) or SIS account ID \
                                  (e.g. sis_account_id:school:hls)')
        parser.add_argument('--enrollment-term-id', nargs='+', required=True,
                            help='Canvas enrollment term id (e.g. 1234) or SIS term ID \
                                  (e.g. sis_term_id:2015-2)')
        parser.add_argument('--output-file', help='File to output mailing list details to')

    def handle(self, *args, **options):
        account_id = options['account_id']
        enrollment_term_id = options['enrollment_term_id']
        output_file = options['output_file']

        if not output_file:
            output_file = './mailing_list/management/commands/report.csv'

        course_data = []

        try:
            courses = get_courses_for_account_in_term(account_id, enrollment_term_id, include_sections=False)
            for course in courses:
                canvas_course_id = course['id']
                # Check if the course has used the Course Emailer tool.
                course_in_mailing_list = MailingList.objects.filter(canvas_course_id=canvas_course_id).exists()
                if course_in_mailing_list:
                    course_data.append([canvas_course_id,])
        except CanvasAPIError as e:
            logger.error(f"Canvas API error: {str(e)}")

        if course_data:
            with open(output_file, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(OUTPUT_FIELDS)
                csv_writer.writerows(course_data)

            self.stdout.write(self.style.SUCCESS(f"CSV report has been generated and saved to {output_file}"))
        else:
            self.stdout.write(self.style.ERROR(f"CSV report has NOT been generated."))
