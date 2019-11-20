import argparse
import logging
from operator import itemgetter

from django.core.management.base import BaseCommand, CommandError

from icommons_common.canvas_utils import UnicodeCSVWriter

from lti_emailer.canvas_api_client import get_courses_for_account_in_term
from mailing_list.models import MailingList
from canvas_sdk.exceptions import CanvasAPIError

OUTPUT_FIELDS = ['id', 'sis_course_id', 'name', 'course_code']

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Activates all mailing lists for a given account and enrollment term'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', required=True,
                            help='Canvas account id (e.g. 29) or SIS account ID \
                                  (e.g. sis_account_id:school:hls)')
        parser.add_argument('--enrollment-term-id', nargs='+', required=True,
                            help='Canvas enrollment term id (e.g. 1234) or SIS term ID \
                                  (e.g. sis_term_id:2015-2)')
        parser.add_argument('--output-file', type=argparse.FileType('w'),
                            help='File to output mailing list details to')

    def handle(self, *args, **options):
        courses = []
        for term_id in options['enrollment_term_id']:
            try:
                courses += get_courses_for_account_in_term(
                    options['account_id'], term_id
                ) or []
            except CanvasAPIError as e:
                # don't raise the error
                pass
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

            # the "is it the primary list" logic varies depending on whether or
            # not the list is crosslisted.  figure out which logic to use
            # before bucketing the lists.
            if any([l['is_course_list'] for l in lists]):
                is_primary = itemgetter('is_course_list')
            else:
                is_primary = itemgetter('is_primary')

            primary, secondary = [], []
            for ml in lists:
                num_lists += 1
                if is_primary(ml):
                    primary.append(ml)
                else:
                    secondary.append(ml)
            course_lists[course['id']] = {
                'primary': primary,
                'secondary': secondary
            }

        if failures:
            for course_id, error_message in failures.items():
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
                             'course_code', 'primary_list',
                             'secondary_lists'))
            for course_id in sorted(course_lists):
                course = courses_by_id[course_id]
                primary = ';'.join([l['address'] for l in course_lists[course_id]['primary']])
                secondary = ';'.join([l['address'] for l in course_lists[course_id]['secondary']])
                row = (
                    str(course_id), str(course['sis_course_id']),
                    course['name'], course['course_code'], primary, secondary
                )
                writer.writerow(row)
