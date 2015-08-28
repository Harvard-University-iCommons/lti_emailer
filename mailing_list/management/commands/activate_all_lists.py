import argparse
import logging

from django.core.management.base import BaseCommand, CommandError

from icommons_common.canvas_utils import UnicodeCSVWriter

from lti_emailer.canvas_api_client import get_courses_for_account_in_term
from mailing_list.models import MailingList


OUTPUT_FIELDS = ['id', 'sis_course_id', 'name', 'course_code']

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Activates all mailing lists for a given account and enrollment term'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, required=True,
                            help='Canvas account id')
        parser.add_argument('--enrollment-term-id', type=int, required=True,
                            help='Canvas enrollment term id')
        parser.add_argument('--output-file', type=argparse.FileType('w'),
                            help='File to output mailing list details to')

    def handle(self, *args, **options):
        try:
            courses = get_courses_for_account_in_term(
                options['account_id'], options['enrollment_term_id']
            )
        except RuntimeError as e:
            raise CommandError(str(e))

        course_lists, failures = {}, {}
        num_lists = 0
        defaults = {'access_level': MailingList.ACCESS_LEVEL_MEMBERS}
        for course in courses:
            try:
                lists = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(
                    course['id'], defaults=defaults
                )
            except RuntimeError as e:
                failures[course['id']] = str(e)
                continue

            primary, secondary = [], []
            for ml in lists:
                num_lists += 1
                if ml['is_primary_section']:
                    primary.append(ml)
                else:
                    secondary.append(ml)
            course_lists[course['id']] = {
                'primary': primary,
                'secondary': secondary
            }

        if failures:
            for course_id, error_message in failures.iteritems():
                logger.error(
                    'Unable to get/create mailing lists for canvas course id {}: {}'.format(course_id, error_message)
                )
            self.stderr.write(
                'Failed to get/create lists for {} courses'.format(len(failures))
            )

        self.stdout.write('Total of {} list(s) for {} course(s)'.format(num_lists, len(courses)))

        if options.get('output_file'):
            courses_by_id = {c['id']: c for c in courses}
            writer = UnicodeCSVWriter(options['output_file'])
            writer.writerow(('canvas_course_id', 'sis_course_id', 'course_name',
                             'course_code', 'primary_section_lists',
                             'secondary_section_lists'))
            for course_id in sorted(course_lists):
                course = courses_by_id[course_id]
                primary = u';'.join([l['address'] for l in course_lists[course_id]['primary']])
                secondary = u';'.join([l['address'] for l in course_lists[course_id]['secondary']])
                row = (
                    unicode(course_id), unicode(course['sis_course_id']),
                    course['name'], course['course_code'], primary, secondary
                )
                writer.writerow(row)