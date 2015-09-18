from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base import EmailerBasePage
from selenium.common.exceptions import NoSuchElementException

# This is the page object for the Main landing page of AB Tool.

# These are page-specific locators.
class Locator1(object):
    # _new_experiment = (By.LINK_TEXT, "New Experiment")
      _h1_selector = (By.CSS_SELECTOR, "h1")


class MainPage(EmailerBasePage):

    def get_title(self):
        """This gets the title of the page you're on to validate the right page loaded"""
        element = self.find_element(*Locator1._h1_selector)
        return element
