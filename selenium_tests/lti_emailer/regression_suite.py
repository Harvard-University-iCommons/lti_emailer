import unittest
import time
import HTMLTestRunner
from os import path, makedirs

from selenium_tests.lti_emailer.Emailer_Permission_Test import EmailerPermissionTest
from selenium_tests.lti_emailer.Emailer_Test_Flow import test_is_loaded


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

is_tool_loaded = unittest.TestLoader().loadTestsFromTestCase(test_is_loaded)
permission_testing = unittest.TestLoader().loadTestsFromTestCase(EmailerPermissionTest)


# create a test suite combining the tests above
smoke_tests = unittest.TestSuite([is_tool_loaded, permission_testing])

# run the suite
runner.run(smoke_tests)
# close test report file
report_file_buffer.close()

