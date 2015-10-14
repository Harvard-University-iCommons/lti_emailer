from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base_page import EmailerBasePage

# These are page-specific locators on Index/Main page.
class EmailerMainPageLocators(object):

    _h1_selector = (By.CSS_SELECTOR, "h1")


class EmailerMainPage(EmailerBasePage):

    def get_title(self):
        element = self.find_element(*EmailerMainPageLocators._h1_selector)
        return element