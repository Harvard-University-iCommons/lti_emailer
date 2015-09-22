__author__ = 'hic048'
import unittest

from selenium.webdriver.support.ui import WebDriverWait
from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_permission_po import PermissionPage, Locator2
from selenium.common.exceptions import TimeoutException


"""
Possible ways to validate permissions:
  1. set up a secure.settings file and set up users in dictionary and log in as those roles.
  2. build a script to add the roster and then masquerade (need check to make sure users not already added)
  3. pre-set up roles and then masquerade (this is the current simple approach set up below)
  Q. Is it possible to connect this test against db permission records? If settings for roles change,
  a way to dynamically change? Need to pick a developer's brain on how best to do this.ion records?
  TODO:  Look into how this can be setup to check against with db records (dynamically driven).
  TODO:  set these ID up in Excel for mod (data driven) and not in code

"""
class RoleTest (object):
    # emailer_url = https://canvas.icommons.harvard.edu/courses/6389/external_tools/1747
    _mailing_list_name = "Mailing List for E-PSCI 333"


class test_permission(EmailerBaseTestCase):

    def test_course_roles_denied_access(self):

        # Course roles that should be denied access:
        # Shopper:  Test13/79592
        # Student:  Test14/79593
        # Guest:  Test7/79588
        # Harvard-Viewer: Test8/79589
        # Observer: Test11/79557
        # SapnaRole:  Test77/79505 (edge case; not a valid role; should be denied access)

        # Masquerading as a role that should not have access to Emailer tool

        deniedroles = ('79592', '79593', '79588', '79589', '79557', '79505')

        for n in deniedroles:
            driver = self.driver
            permission = PermissionPage(driver) #instantiate
            # get masqueraded URL for Canvas user
            URL = "https://canvas.icommons.harvard.edu/users/" + n + "/masquerade"
            driver.get(URL)
            # and masquerade as user
            permission.masquerade_confirm()
            # go to emailer tool as masqueraded user
            permission.get_emailer_URL()
            permission.switch_frame()
            # driver.save_screenshot("unauth" + n + ".png")
            print "Validating denied access for course level roles/ Canvas user ID:" + n
            self.assertEqual("Unauthorized", permission.unauth_message(), "Error: Did not get unauth error for" + n)



    def test_course_roles_granted_access(self):
        # Course roles that should be granted access
        # TA:  Test15/79494
        # Teaching Staff: Test16/79594
        # Course Head:  Test2/79584
        # Course Support Staff: Test3/79585
        # Course Designer: Test5/79577
        # Faculty:  Test6/79587

        # Masquerading as a role that should have access to view Emailer Tool
        grantedroles = ('79494', '79594', '79584', '79585', '79587','79577')
        for y in grantedroles:
            driver = self.driver
            permission = PermissionPage(driver) #instantiate
            # get masqueraded URL for Canvas user
            URL = "https://canvas.icommons.harvard.edu/users/" + y + "/masquerade"
            driver.get(URL)
            # and masquerade as user
            permission.masquerade_confirm()
            # go to emailer tool as masqueraded user
            permission.get_emailer_URL()
            # driver.save_screenshot("auth" + y + ".png")
            print "Validating granted access for course level roles/ Canvas user ID:" + y
            permission.switch_frame()
            # Wait for element to be found; else test will fail
            try:
                WebDriverWait(driver, 10).until(lambda s: s.find_element(*Locator2._pageload).is_displayed())
            except TimeoutException:
                return False
            self.assertEqual(RoleTest._mailing_list_name, permission.auth_page(), "Error: did not find Emailer Tool for" + y)


    def test_account_level_roles_granted_access(self):
        # ACCOUNT-level roles that should be granted access:
        # For subaccount 656: https://canvas.icommons.harvard.edu/accounts/656/settings
        # AccountAdmin:  test33/79610
        # SchoolLiaison:  test34/79611
        # Department Admin/Helpdesk/Librarian:  Roles do not exist in QA/did not test

        # Masquerading as ACCOUNT level role that should have access to view Emailer Tool
        account_level_roles = ('79611', '79610')
        for z in account_level_roles:
            driver = self.driver
            permission = PermissionPage(driver) #instantiate
            # get masqueraded URL for Canvas user
            URL = "https://canvas.icommons.harvard.edu/users/" + z + "/masquerade"
            driver.get(URL)
            # and masquerade as user
            permission.masquerade_confirm()
            # go to emailer tool as masqueraded user
            permission.get_emailer_URL()
            driver.save_screenshot("account_admin_" + z + ".png")
            print "Validating granted access for account level roles/ Canvas user ID:" + z
            permission.switch_frame()
            # Wait for element to be found; else test will fail
            try:
              WebDriverWait(driver, 10).until(lambda s: s.find_element(*Locator2._pageload).is_displayed())
            except TimeoutException:
                return False
            self.assertEqual(RoleTest._mailing_list_name, permission.auth_page(), "Error: did not find Emailer Tool for" + z)


if __name__ == "__main__":
    unittest.main()





