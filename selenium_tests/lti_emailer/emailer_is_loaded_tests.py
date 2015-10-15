import unittest

from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_mainpage_page_object import EmailerMainPage


class EmailerIsLoadedTests(EmailerBaseTestCase):

    def test_tool_is_loaded_on_page(self):
        """Check that page is loaded by checking against site title"""
        driver = self.driver
        page = EmailerMainPage(driver)  # instantiate
        element = page.get_title()
        page_title = "Course Emailer"
        print "Verifying page title..."
        self.assertEqual(element.text, page_title,
                         "Error: Wrong page. Expected page title is '{}' but page title is returning '{}'"
                         .format(page_title, element.text))


if __name__ == "__main__":
    unittest.main()