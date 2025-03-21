import csv
import logging
from argparse import ArgumentParser
from typing import Any, Dict

from coursemanager.models import CourseInstance
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from mailing_list.models import MailingList

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generates a CSV report of courses that have used the Course Emailer tool. \
            Filters by academic years (required), school (optional), and can include \
            ongoing courses. Output includes course details such as school ID, course ID, \
            Canvas course ID, term ID, title, instructors, and cross-listing status.'

    ONGOING_TERM_YEAR = '1900'
    DEFAULT_OUTPUT_FILE = './mailing_list/management/commands/report.csv'

    def add_arguments(self, parser: ArgumentParser) -> None:
        """ Command-line argument definitions."""
        parser.add_argument('--school', required=False,
                            help='Canvas account school id (e.g. hls). If not provided, all schools will be included.')
        parser.add_argument('--academic-years', nargs='+', required=True,
                            help='Canvas enrollment academic year (e.g. 2025)')
        parser.add_argument('--include-ongoing', action='store_true',
                            help='Include ongoing courses (with academic year value of 1900)')
        parser.add_argument('--output-file', required=False,
                            help='File to output mailing list details to')

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        """
        Generates a CSV report of courses that have utilized the \
        Course Emailer tool within a specified school and academic years.
        """
        # Retrieve command-line arguments
        school = options.get('school')
        academic_years = options['academic_years']
        include_ongoing = options.get('include_ongoing', False)
        output_file = options['output_file'] if options['output_file'] else self.DEFAULT_OUTPUT_FILE

        # Validate academic years
        for year in academic_years:
            try:
                int(year)
            except ValueError:
                raise CommandError(f"Invalid academic year: {year}. Years must be integers.")

        earliest_academic_year = min(int(year) for year in academic_years)
        start_date = timezone.datetime(earliest_academic_year, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Retrieve canvas course ids in mailing list. Mailing list records are
        # created in the database once a course start using the Course Emailer tool.
        canvas_course_id_list = list(MailingList.objects.filter(
            date_created__gte=start_date).values_list('canvas_course_id', flat=True).distinct())
        print(f"======>>> Canvas course ID list since {earliest_academic_year} from mailing list. Total: {len(canvas_course_id_list)}")
        # Build query filters
        query_filters = {
            'canvas_course_id__in': canvas_course_id_list,
            'sync_to_canvas': 1
        }

        # Add academic year filter
        if include_ongoing:
            query_filters['term__academic_year__in'] = academic_years + [self.ONGOING_TERM_YEAR]
            print(f"======>>> Including ongoing term ({self.ONGOING_TERM_YEAR}) in academic years.")
        else:
            query_filters['term__academic_year__in'] = academic_years
        
        # Add school filter only if a specific school is provided
        if school:
            query_filters['course__school_id'] = school
            school_message = f"for school '{school}'"
        else:
            school_message = "for all schools"
        
        # Query CourseInstance based on filters
        course_instances = CourseInstance.objects.filter(**query_filters)
        print(f"======>>> Total course instances using Course Emailer {school_message}: {len(course_instances)}")

        # Iterate through course instances and collect relevant data.
        course_data = []
        for course_instance in course_instances:
            course_data.append([course_instance.course.school_id,
                                course_instance.course_instance_id,
                                course_instance.canvas_course_id,
                                course_instance.term_id,
                                course_instance.title,
                                course_instance.instructors_display,
                                course_instance.xlist_flag])

        # Define the fields for the CSV.
        OUTPUT_FIELDS = ['school_id', 'course_instance_id', 'canvas_course_id',
                         'term_id', 'title', 'instructors_display', 'xlist_flag']

        # Save data to CSV file.
        if course_data:
            try:
                with open(output_file, 'w', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(OUTPUT_FIELDS)
                    csv_writer.writerows(course_data)

                self.stdout.write(self.style.SUCCESS(f"CSV report has been generated and saved to {output_file}"))
            except IOError as e:
                self.stdout.write(self.style.ERROR(f"Error writing to file {output_file}: {str(e)}"))
        else:
            school_filter = f"school '{school}'" if school else "all schools"
            years_str = ", ".join(academic_years)
            ongoing_str = "including ongoing courses" if include_ongoing else "excluding ongoing courses"
            self.stdout.write(self.style.WARNING(
                f"No data found for {school_filter} in academic years {years_str} ({ongoing_str})."
            ))
