from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base_page import EmailerBasePage
from django.conf import settings

# These are page-specific locators.
class PermissionServiceLocators(object):

    _emailer_url = '%s/courses/6389/external_tools/1759' % settings.SELENIUM_CONFIG.get('base_url')
    _masquerade_url_base = '%s/users/' % settings.SELENIUM_CONFIG.get('base_url')
    _mailing_list_name = "Mailing Lists for Earth and Planetary Sciences 333: Environmental Chemistry"
    _confirm_mask = (By.CSS_SELECTOR, "a.btn.masquerade_button")
    _unauthstate = (By.CSS_SELECTOR, "h2.ui-state-error")
    _authstate = (By.CSS_SELECTOR, "h2")
    _switchframe = (By.ID, "tool_content")
    _pageload = (By.CSS_SELECTOR, "h2")
    _validate_denied_msg = "Validating denied access for course level roles/ Canvas user ID:"
    _validate_access_msg = "Validating access for Canvas user ID:"


class PermissionService(EmailerBasePage):


    def switch_frame(self):
        driver = self._driver
        driver.switch_to.frame(driver.find_element(*PermissionServiceLocators._switchframe))

    def check_for_denied_access(self):
        # this checks and returns the Canvas unauthorized message if user do not have access to Emailer
        unauth = self.find_element(*PermissionServiceLocators._unauthstate)
        return unauth.text

    def check_for_granted_access(self):
        # this checks and returns Emailer header text on webpage if user can get to the Emailer access.
        auth = self.find_element(*PermissionServiceLocators._authstate)
        return auth.text

    def get_emailer_url(self):
        self.get(PermissionServiceLocators._emailer_url)

    def confirm_masquerade(self):
        masquerade = self.find_element(*PermissionServiceLocators._confirm_mask)
        masquerade.click()