import unittest

from selenium_tests.lti_emailer.Emailer_Base_Test_Case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_mainpage import MainPage


class EmailerTestFlow (EmailerBaseTestCase):

    def test_is_loaded(self):
        """Check that page is loaded by checking against site title"""
        driver = self.driver
        page = MainPage(driver)  # instantiate
        element = page.get_title()
        page_title = "Course Emailer"
        print "Verifying page title..."
        self.assertEqual(element.text, page_title, "Error: Wrong page. Expected page title is '{}' but "
                                                   "page title is returning '{}'".format(page_title, element.text))


if __name__ == "__main__":
    unittest.main()