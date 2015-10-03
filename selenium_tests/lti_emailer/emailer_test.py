__author__ = 'hic048'

import unittest

from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_mainpage import MainPage, Locator1

class test_is_loaded(EmailerBaseTestCase):

    def test_is_loaded (self):
        """Check that page is loaded by checking against site title of "Course Emailer"""
        driver = self.driver
        page = MainPage(driver) #instantiate
        element = page.get_title()
        emailertext = "Course Emailer"
        print "Verifying page title..."
        self.assertEqual(element.text, emailertext, "Error: Wrong page. Expected page title is '{}' but"
                                               " page title is returning '{}'".format(emailertext, element.text))


if __name__ == "__main__":
    unittest.main()

