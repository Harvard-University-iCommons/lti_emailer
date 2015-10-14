import unittest

from ddt import ddt, data, unpack

from selenium_tests.lti_emailer.Emailer_Base_Test_Case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_test_setup_po import EmailerTestSetupPO, EmailerTestSetupLocators
from selenium_tests.lti_emailer.Emailer_Base_Test_Case import CANVAS_ROLES
from selenium_tests.base_test_case import get_xl_data


@ddt
class EmailerTestSetup(EmailerBaseTestCase):

    @data(*get_xl_data(CANVAS_ROLES))
    @unpack
    def test_add_user_setup(self, user_id, roles):

        """This adds a list of predefined users to specific roles according /test_data/roles.xlsx."""
        test_setup = EmailerTestSetupPO(self.driver)
        test_setup.add_users(user_id, roles)  # adding users to from data file
        test_setup.confirm_add()  # confirming add
        print user_id + " added to " + EmailerTestSetupLocators._add_people_url

if __name__ == "__main__":
    unittest.main()