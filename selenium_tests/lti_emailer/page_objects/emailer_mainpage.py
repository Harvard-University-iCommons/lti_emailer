from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base import EmailerBasePage

# These are page-specific locators.
class Locator1(object):
      _h1_selector = (By.CSS_SELECTOR, "h1")
      _emailer_list = (By.ID, "email-section-1670")



class MainPage(EmailerBasePage):

    def get_title(self):
        element = self.find_element(*Locator1._h1_selector)
        return element

    def get_addy(self):
        email_list = self.find_element(*Locator1._emailer_list)
        return email_list.text




