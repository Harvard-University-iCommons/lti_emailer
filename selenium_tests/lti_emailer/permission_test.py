__author__ = 'hic048'
import unittest
from ddt import ddt, data, unpack

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium_tests.base_test_case import get_xl_data
from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_permission_po import PermissionPage, Locator2
from selenium_tests.lti_emailer.emailer_base_test_case import CANVAS_ADD_USERS


class RoleTest (object):
    _mailing_list_name = "Mailing List for E-PSCI 333"
    _masquerade_url_base = "https://canvas.icommons.harvard.edu/users/"
    _validate_denied_msg = "Validating denied access for course level roles/ Canvas user ID:"
    _validate_access_msg = "Validating access for Canvas user ID:"

@ddt

class test_permission(EmailerBaseTestCase):
    @data(*get_xl_data(CANVAS_ADD_USERS))
    @unpack
    # This test masquerades as users in roles specified defined in /test_data/roles_access.xlsx
    # The test then validates if the users are granted/denied access based on their role.
    # Emailer URL =  https://canvas.icommons.harvard.edu/courses/6389/external_tools/1759

    def test_roles_access(self, user_id, given_access):
        driver = self.driver
        permission = PermissionPage(driver) #instantiate
        # Loop over the list of roles that should be denied access to the Emailer Tool
        for n in self, int(user_id):
            if given_access == 'no':
                driver = self.driver
                # Get masquerade URL for Canvas user and masquerade as user
                url = RoleTest._masquerade_url_base + str(user_id) + "/masquerade"
                driver.get(url)
                permission.masquerade_confirm()
                # Go to emailer tool as masqueraded user and verify denied access
                permission.get_emailer_URL()
                permission.switch_frame()
                print RoleTest._validate_denied_msg + str(user_id)
                self.assertEqual("Unauthorized", permission.unauth_message(),
                                 "Error: Did not get unauth error for" + str(user_id))

            elif given_access == 'yes':
                driver = self.driver
                permission = PermissionPage(driver) #instantiate
                # Get masqueraded URL for Canvas user and masquerade as user
                url = RoleTest._masquerade_url_base + str(user_id) + "/masquerade"
                driver.get(url)
                permission.masquerade_confirm()
                # Go to emailer tool as masqueraded user and verify access
                permission.get_emailer_URL()
                print RoleTest._validate_access_msg + str(user_id)
                permission.switch_frame()
                # Wait for element to be found; else test will fail
                try:
                    WebDriverWait(driver, 10).until(lambda s: s.find_element(*Locator2._pageload).is_displayed())
                except TimeoutException:
                    return False
                self.assertEqual(RoleTest._mailing_list_name, permission.auth_page(),
                                 "Error: did not find Emailer Tool for: " + str(user_id))



if __name__ == "__main__":
    unittest.main()


