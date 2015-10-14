__author__ = 'hic048'

from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base import EmailerBasePage


# These are page-specific locators.
class PermissionServiceLocators(object):
      _emailer_url = "https://canvas.icommons.harvard.edu/courses/6389/external_tools/1759"
      _confirm_mask = (By.CSS_SELECTOR, "a.btn.masquerade_button")
      _unauthstate = (By.CSS_SELECTOR, "h2.ui-state-error")
      _authstate = (By.CSS_SELECTOR, "h2")
      _switchframe = (By.ID, "tool_content")
      _pageload = (By.CSS_SELECTOR, "h2")
      _mailing_list_name = "Mailing Lists for Earth and Planetary Sciences 333: Environmental Chemistry"
      _masquerade_url_base = "https://canvas.icommons.harvard.edu/users/"
      _validate_denied_msg = "Validating denied access for course level roles/ Canvas user ID:"
      _validate_access_msg = "Validating access for Canvas user ID:"


class EmailerPermissionService(EmailerBasePage):

    def switch_frame(self):
        driver = self._driver
        driver.switch_to.frame(driver.find_element(*PermissionServiceLocators._switchframe))

    def unauth_message(self):
        # this returns the unauthorized message on the unauthorized screen
        unauth = self.find_element(*PermissionServiceLocators._unauthstate)
        unauth = unauth.text
        return unauth

    def auth_page(self):
        # this returns the Email header on the emailer page
        auth = self.find_element(*PermissionServiceLocators._authstate)
        auth = auth.text
        return auth

    def get_emailer_URL(self):
        self.get(PermissionServiceLocators._emailer_url)

    def masquerade_confirm(self):
        mask = self.find_element(*PermissionServiceLocators._confirm_mask)
        mask.click()



