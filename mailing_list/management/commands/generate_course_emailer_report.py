import csv
import logging

from coursemanager.models import CourseInstance
from django.core.management.base import BaseCommand

from mailing_list.models import MailingList

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generates a CSV report for Course Emailer list of courses that \
            have used Course Emailer for specified school and academic years'

    def add_arguments(self, parser):
        """ Command-line argument definitions."""
        parser.add_argument('--school', required=True,
                            help='Canvas account school id (e.g. hls)')
        parser.add_argument('--academic-years', nargs='+', required=True,
                            help='Canvas enrollment academic year (e.g. 2023)')
        parser.add_argument('--output-file',
                            help='File to output mailing list details to')

    def handle(self, *args, **options) -> None:
        """
        Generates a CSV report for Course Emailer list of courses that \
        have used Course Emailer for specified school and academic years.
        """
        # Retrieve command-line arguments
        school = options['school']
        academic_years = options['academic_years']
        output_file = options['output_file'] if options['output_file'] else './mailing_list/management/commands/report.csv'

        # Retrieve canvas course ids in mailing list. Mailing list records are
        # created in the database once a course start using the Course Emailer tool.
        canvas_course_id_list = list(MailingList.objects.filter(
            date_created__gte='2022-01-01 00:00:00').values_list('canvas_course_id', flat=True))
        print(f"======>>> canvas_course_id_list total: {len(canvas_course_id_list)}")

        # Query CourseInstance based on school, academic years, and terms
        course_instances = CourseInstance.objects.filter(
            course__school_id=school, term__academic_year__in=academic_years,
            canvas_course_id__in=canvas_course_id_list, sync_to_canvas=1)
        print(f"======>>> course_instances total: {len(course_instances)}")

        # Iterate through course instances and collect relevant data.
        course_data = []
        for course_instance in course_instances:
            course_data.append([course_instance.course_instance_id,
                                course_instance.canvas_course_id,
                                course_instance.term_id,
                                course_instance.title,
                                course_instance.instructors_display,
                                course_instance.xlist_flag])

        # Define the fields for the CSV.
        OUTPUT_FIELDS = ['course_instance_id', 'canvas_course_id', 'term_id',
                         'title', 'instructors_display', 'xlist_flag']

        # Save data to CSV file.
        if course_data:
            with open(output_file, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(OUTPUT_FIELDS)
                csv_writer.writerows(course_data)

            self.stdout.write(self.style.SUCCESS(f"CSV report has been generated and saved to {output_file}"))
        else:
            self.stdout.write(self.style.ERROR(f"ERROR CSV report has NOT been generated."))
