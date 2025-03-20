# generate_course_emailer_report.py

- `generate_course_emailer_report` is a Django management command designed to create a CSV report of courses that have utilized the Course Emailer tool.
- The report includes course details such as school ID, course ID, Canvas course ID, term ID, title, instructors, and cross-listing status.

### Arguments

- `--academic-years`: **Required** - Specify one or more academic years for which to generate the report (e.g., "2024 2025").

- `--school`: Optional - Specify the Canvas account school ID (e.g., "hls"). If not provided, courses from all schools will be included in the report.

- `--include-ongoing`: Optional flag - Include ongoing courses (with academic year value of 1900) in the report.

- `--output-file`: Optional - Specify the path for the output CSV file. If not provided, the default path is "./mailing_list/management/commands/report.csv".

### Examples commands

1. Generate a report for a specific school and academic years:
```
python manage.py generate_course_emailer_report --school hsph --academic-years 2024 2025
```
2. Generate a report for all schools in a specific academic year:
```
python manage.py generate_course_emailer_report --academic-years 2025
```
3. Include ongoing courses in the report:
```
python manage.py generate_course_emailer_report --academic-years 2025 --include-ongoing
```
4. Specify a custom output file:
```
python manage.py generate_course_emailer_report --academic-years 2025 --output-file /path/to/custom_report.csv
```
