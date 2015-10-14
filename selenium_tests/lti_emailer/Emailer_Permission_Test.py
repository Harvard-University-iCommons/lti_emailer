import unittest
from ddt import ddt, data, unpack

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium_tests.base_test_case import get_xl_data
from selenium_tests.lti_emailer.Emailer_Base_Test_Case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_permission_service import PermissionServiceLocators, EmailerPermissionService
from selenium_tests.lti_emailer.Emailer_Base_Test_Case import CANVAS_ADD_USERS


@ddt
class EmailerPermissionTest(EmailerBaseTestCase):

    @data(*get_xl_data(CANVAS_ADD_USERS))
    @unpack
    def test_roles_access(self, user_id, given_access):
        """This test masquerades as users in roles in /test_data file defined by variable CANVAS_ADD_USERS"""

        permission = EmailerPermissionService(self.driver)  # instantiate
        # Loop over the list of roles that should be denied access to the Emailer Tool
        if given_access == 'no':
            # Get masquerade URL for Canvas user and masquerade as user
            url = PermissionServiceLocators._masquerade_url_base + str(user_id) + "/masquerade"
            self.driver.get(url)
            permission.masquerade_confirm()
            # Go to email tool as masqueraded user and verify denied access
            permission.get_emailer_URL()
            permission.switch_frame()
            print PermissionServiceLocators._validate_denied_msg + str(user_id)
            self.assertEqual("Unauthorized", permission.unauth_message(),
                             "Error: Did not get unauth error for" + str(user_id))

        elif given_access == 'yes':
            permission = EmailerPermissionService(self.driver)  # instantiate
            # Get masqueraded URL for Canvas user and masquerade as user
            url = PermissionServiceLocators._masquerade_url_base + str(user_id) + "/masquerade"
            self.driver.get(url)
            permission.masquerade_confirm()
            # Go to email tool as masqueraded user and verify access
            permission.get_emailer_URL()
            print PermissionServiceLocators._validate_access_msg + str(user_id)
            permission.switch_frame()
            # Wait for element to be found; else test will fail
            try:
                WebDriverWait(self.driver, 10).until(lambda s: s.find_element(*PermissionServiceLocators._pageload)
                                                     .is_displayed())
            except TimeoutException:
                return False
            self.assertEqual(PermissionServiceLocators._mailing_list_name, permission.auth_page(),
                             "Error: Cannot verify Emailer Tool for: " + str(user_id))

if __name__ == "__main__":
    unittest.main()