__author__ = 'hic048'
import unittest
from ddt import ddt, data, unpack

from selenium_tests.lti_emailer.Emailer_Base_Test_Case import EmailerBaseTestCase
from selenium.webdriver.support.ui import Select
from selenium_tests.lti_emailer.page_objects.add_user_po import UserAdd, Locator3
from selenium_tests.lti_emailer.Emailer_Base_Test_Case import CANVAS_ROLES
from selenium_tests.base_test_case import get_xl_data

# BASE_URL = /courses/6389/external_tools/1759
#URL = "http://canvas.icommons.harvard.edu/courses/6389/users"

@ddt
class Addingusers(EmailerBaseTestCase):
    # This adds a list of predefined users to specific roles according to /test data/roles.xlsx.
    # If this list of users need to be populated on another course, locator "_add_people_url" needs
    # to be updated. For testing with large data add, please refer to team wiki.
    @data(*get_xl_data(CANVAS_ROLES))
    @unpack
    def test_user_setup(self, user_id, roles):
        for n in self, user_id, roles:
            driver = self.driver
            print "adding " + user_id + "to " + Locator3._add_people_url
            adduser = UserAdd(driver) #instantiate
            # Go to people page and click on add user
            adduser.get(Locator3._add_people_url)
            adduser.find_user_add()
            # Adding user_id from spreadsheet
            textarea = driver.find_element(*Locator3._addtextarea)
            textarea.send_keys(user_id)
            Select(driver.find_element(*Locator3._canvas_role)).select_by_visible_text(roles)
            # Adding roles from spreadsheet
            adduser.confirm_add()



if __name__ == "__main__":
    unittest.main()


