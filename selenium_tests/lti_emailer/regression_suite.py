"""
To run these tests from the command line in a local VM, you'll need to set up the environment:
> export PYTHONPATH=/home/vagrant/icommons_lti_tools
> export DJANGO_SETTINGS_MODULE=icommons_lti_tools.settings.local
> sudo apt-get install xvfb
> python selenium_tests/regression_tests.py

Or for just one set of tests, for example:
> python selenium_tests/manage_people/mp_test_search.py

In PyCharm, if xvfb is installed already, you can run them through the Python unit test run config
(make sure the above environment settings are included)
"""

import unittest
import time
import HTMLTestRunner

from selenium_tests.lti_emailer.permission_test import test_permission
from selenium_tests.lti_emailer.emailer_test import test_is_loaded


date_timestamp = time.strftime('%Y%m%d_%H_%M_%S')


buf = file("TestReport" + "_" + date_timestamp + ".html", 'wb')
runner = HTMLTestRunner.HTMLTestRunner(
    stream=buf,
    title='Test the Report',
    description='Result of tests'
)

is_tool_loaded = unittest.TestLoader().loadTestsFromTestCase(test_is_loaded)
permission_testing = unittest.TestLoader().loadTestsFromTestCase(test_permission)


# create a test suite combining the tests above
smoke_tests = unittest.TestSuite([is_tool_loaded, permission_testing])

# run the suite
runner.run(smoke_tests)
# close test report file
buf.close()

