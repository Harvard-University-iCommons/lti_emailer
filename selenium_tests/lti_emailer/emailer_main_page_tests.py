import unittest

from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_mainpage_page_object import EmailerMainPage


class EmailerMainPageTests(EmailerBaseTestCase):

    def test_tool_is_loaded_on_page(self):
        """Check that page is loaded by checking against site title"""
        driver = self.driver
        page = EmailerMainPage(driver)  # instantiate
        page.is_loaded()

if __name__ == "__main__":
    unittest.main()