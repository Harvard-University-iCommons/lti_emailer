import unittest
import time
from os import path, makedirs

from selenium_common import HTMLTestRunner
from selenium_tests.lti_emailer.emailer_permission_tests import EmailerPermissionTests


class RegressionSuite(unittest.TestCase):
    def main(self):

        date_timestamp = time.strftime('%Y%m%d_%H_%M_%S')

        # This relative path should point to BASE_DIR/selenium_tests/reports
        report_file_path = path.relpath('../reports')
        if not path.exists(report_file_path):
            makedirs(report_file_path)
        report_file_name = "lti_emailer_test_report_{}.html".format(date_timestamp)
        report_file_buffer = file(path.join(report_file_path, report_file_name), 'wb')
        runner = HTMLTestRunner.HTMLTestRunner(
            stream=report_file_buffer,
            title='LTI emailer test suite report',
            description='Result of tests in {}'.format(__file__)
        )

        permission_testing = unittest.TestLoader().loadTestsFromTestCase(EmailerPermissionTests)

        # create a test suite combining the tests above
        smoke_tests = unittest.TestSuite([permission_testing])

        # run the suite
        runner.run(smoke_tests)
        # close test report file
        report_file_buffer.close()

if __name__ == "__main__":
    unittest.main()
