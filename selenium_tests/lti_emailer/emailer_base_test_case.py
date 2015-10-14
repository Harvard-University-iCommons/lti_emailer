from urlparse import urljoin
from selenium_tests.base_test_case import BaseSeleniumTestCase
from selenium_tests.lti_emailer.page_objects.pin_login import PinLogin
from selenium_tests.lti_emailer.page_objects.emailer_mainpage import EmailerMainPage

from os.path import abspath, dirname, join
from django.conf import settings


CANVAS_ADD_USERS = join(dirname(abspath(__file__)), 'test_data', 'roles_access.xlsx')
CANVAS_ROLES = join(dirname(abspath(__file__)), 'test_data', 'roles.xlsx')


class EmailerBaseTestCase(BaseSeleniumTestCase):
    """Emailer base test case, all other tests will subclass this class"""

    @classmethod
    def setUpClass(cls):
        """
        setup values for the tests
        """
        super(EmailerBaseTestCase, cls).setUpClass()
        driver = cls.driver
        cls.USERNAME = settings.SELENIUM_CONFIG.get('selenium_username')
        cls.PASSWORD = settings.SELENIUM_CONFIG.get('selenium_password')
        cls.CANVAS_BASE_URL = settings.SELENIUM_CONFIG.get('canvas_base_url')
        cls.TOOL_RELATIVE_URL = settings.SELENIUM_CONFIG.get('emailer_tool_relative_url')
        cls.TOOL_URL = urljoin(cls.CANVAS_BASE_URL, cls.TOOL_RELATIVE_URL)

        cls.emailer_main_page = EmailerMainPage(driver)
        cls.emailer_main_page.get(cls.TOOL_URL)
        login_page = PinLogin(driver)
        if login_page.is_loaded():
            login_page.login(cls.USERNAME, cls.PASSWORD)
        else:
            print '(User {} already logged in to PIN)'.format(cls.USERNAME)
