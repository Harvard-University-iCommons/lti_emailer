import unittest
import time
import os

from selenium_common import HTMLTestRunner

def main():

    date_timestamp = time.strftime('%Y%m%d_%H_%M_%S')

    # set up PYTHONPATH and DJANGO_SETTINGS_MODULE.  icky, but necessary
    os.sys.path.insert(0, os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..')))
    if not os.getenv('DJANGO_SETTINGS_MODULE'):
        os.putenv('DJANGO_SETTINGS_MODULE', 'lti_emailer.settings.local')

    # This relative path should point to BASE_DIR/selenium_tests/reports
    report_file_path = os.path.relpath('./reports')
    if not os.path.exists(report_file_path):
        os.makedirs(report_file_path)
    report_file_name = "lti_emailer_test_report_{}.html".format(date_timestamp)
    report_file_obj = file(os.path.join(report_file_path, report_file_name), 'wb')
    runner = HTMLTestRunner.HTMLTestRunner(
        stream=report_file_obj,
        title='LTI emailer test suite report',
        description='Result of tests in {}'.format(__file__)
    )

    suite = unittest.defaultTestLoader.discover(
        os.path.abspath(os.path.dirname(__file__)),
        pattern = '*_tests.py',
        top_level_dir=os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))
    )

    # run the suite
    runner.run(suite)
    # close test report file
    report_file_obj.close()

if __name__ == "__main__":
    main()
