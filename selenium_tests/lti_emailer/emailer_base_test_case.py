from django.conf import settings

from selenium_tests.base_test_case import BaseSeleniumTestCase
from selenium_tests.lti_emailer.page_objects.pin_page import LoginPage


class EmailerBaseTestCase(BaseSeleniumTestCase):
    """
    Bulk Create base test case, all other tests will subclass this class
    """

    @classmethod
    def setUpClass(cls):
        """
        setup values for the tests
        """
        super(EmailerBaseTestCase, cls).setUpClass()
        driver = cls.driver
        cls.USERNAME = settings.SELENIUM_CONFIG.get('selenium_username')
        cls.PASSWORD = settings.SELENIUM_CONFIG.get('selenium_password')
        cls.BASE_URL = '%s/courses/6389/external_tools/1747' % settings.SELENIUM_CONFIG.get('base_url')
        #https://canvas.icommons.harvard.edu/courses/6389/external_tools/1747 (site to use for automation)

        #instantiate, then login to URL with username and password from settings, if running locally.
        base_login = LoginPage(driver) # instantiate
        base_login.get(cls.BASE_URL)
        base_login.login(cls.USERNAME, cls.PASSWORD)




