from urlparse import urljoin
from os.path import abspath, dirname, join
from django.conf import settings
import logging
from selenium_common.base_test_case import BaseSeleniumTestCase
from selenium_common.pin.page_objects.pin_login_page_object import PinLoginPageObject
from selenium_tests.lti_emailer.page_objects.emailer_mainpage_page_object import EmailerMainPage
from canvas_sdk.methods.external_tools import (get_single_external_tool_courses,create_external_tool_courses,
                                               delete_external_tool_courses)
from canvas_sdk.exceptions import CanvasAPIError
from icommons_common.canvas_utils import SessionInactivityExpirationRC

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)
logging.basicConfig()
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

        tool_does_not_exist = False
        new_course_id = 0

        # using this exernal tool id for the Manage People tests
        dev_external_tool_id = '1528'

        driver = cls.driver
        cls.USERNAME = settings.SELENIUM_CONFIG.get('selenium_username')
        cls.PASSWORD = settings.SELENIUM_CONFIG.get('selenium_password')
        cls.CANVAS_BASE_URL = settings.SELENIUM_CONFIG.get('canvas_base_url')
        cls.TOOL_RELATIVE_URL = settings.SELENIUM_CONFIG.get('emailer_tool_relative_url')
        cls.TOOL_URL_BASE_RELATIVE = urljoin(cls.CANVAS_BASE_URL, cls.TOOL_RELATIVE_URL)
        # cls.EXTERNAL_TOOL_ID = settings.SELENIUM_CONFIG.get('emailer_tool_id')
        cls.EXTERNAL_TOOL_ID = '747575757'
        cls.COURSE_ID = settings.SELENIUM_CONFIG.get('emailer_course_id')

        ### Verify that the tool_id exist
        try:
            resp= get_single_external_tool_courses(SDK_CONTEXT,
                                                   course_id=cls.COURSE_ID,
                                                   external_tool_id=cls.EXTERNAL_TOOL_ID)
            print "This is the response from SDK using external id %s. Response=%s", cls.EXTERNAL_TOOL_ID, resp
        except CanvasAPIError as api_error:
            tool_does_not_exist = True
            logger.error(
                "CanvasAPIError in retrieving the external tool id %s from course %s. Exception=%s:",
                cls.EXTERNAL_TOOL_ID, cls.COURSE_ID, api_error
            )

        ### if the tool does not exist, go ahead and add the tool back to the course
        if tool_does_not_exist:

            name='Emailer Tool Automation'
            domain="lti-emailer.qa.tlt.harvard.edu"
            config_url='http://lti-emailer.qa.tlt.harvard.edu/tool_config'

            request_parameters = dict(
                request_ctx=SDK_CONTEXT,
                course_id = cls.COURSE_ID,
                name = name,
                privacy_level = 'public',
                consumer_key = 'test',
                shared_secret = 'secret',
                domain = domain,
                config_type = 'by_url',
                config_url=config_url,
            )

            try:
                new_course_resp = create_external_tool_courses(**request_parameters)
                new_course_json = new_course_resp.json()
                print "new course:", new_course_json
                new_course_id = new_course_json[0]['id']
                cls.EXTERNAL_TOOL_ID = str(new_course_id)
            except CanvasAPIError as api_error:
                logger.exception(
                    'Error building request_parameters or executing create_external_tool_courses() '
                    'SDK call for new external tool with request=%s: for course %s. Exception=%s',
                    request_parameters, cls.COURSE_ID, api_error
                )

        print 'new course id is', new_course_id
        cls.TOOL_URL = urljoin(cls.TOOL_URL_BASE_RELATIVE, cls.EXTERNAL_TOOL_ID)
        print 'this is the current url', cls.TOOL_URL
        cls.emailer_main_page = EmailerMainPage(driver)
        cls.emailer_main_page.get(cls.TOOL_URL)
        login_page = PinLoginPageObject(driver)
        if login_page.is_loaded():
            login_page.login_xid(cls.USERNAME, cls.PASSWORD)
        else:
            print '(User {} already logged in to PIN)'.format(cls.USERNAME)

    @classmethod
    def tearDownClass(cls):
        super(EmailerBaseTestCase, cls).tearDownClass()

        try:
            resp = delete_external_tool_courses(SDK_CONTEXT,
                                                course_id=cls.COURSE_ID,
                                                external_tool_id=cls.EXTERNAL_TOOL_ID)
            print "Successful Delete:", resp
        except CanvasAPIError as api_error:
            logger.error(
                "CanvasAPIError in deleting the external tool id %s from course %s. Exception=%s:",
                cls.EXTERNAL_TOOL_ID, cls.COURSE_ID, api_error
            )
