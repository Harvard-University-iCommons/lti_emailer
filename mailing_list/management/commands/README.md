# generate_course_emailer_report.py
- `generate_course_emailer_report` is a Django management command designed to create a CSV report of courses that have utilized the Course Emailer tool within a specified school and academic years.
- To run this management command, you can use the following command:
    ```
    python manage.py generate_course_emailer_report --school <school_id> --academic-years <academic_year1> <academic_year2> --output-file <output_file>
    ```
    - `--school`: Required argument to specify the Canvas account school ID, e.g., "hsph".
    - `--academic-years`: Required argument to provide a list of academic years, e.g., "2023 2024".
    - `--output-file`: Optional argument to specify the path of the output CSV file. If not provided, the default path is "./mailing_list/management/commands/report.csv".
    - Example:
        ```
        python manage.py generate_course_emailer_report --school hsph --academic-years 2023 2024
        ```
