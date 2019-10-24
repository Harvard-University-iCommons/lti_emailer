from urllib.parse import urljoin
from os.path import abspath, dirname, join
from django.conf import settings
import logging
from selenium_common.base_test_case import BaseSeleniumTestCase
from selenium_common.pin.page_objects.pin_login_page_object \
    import PinLoginPageObject
from selenium_common.canvas.canvas_masquerade_page_object \
    import CanvasMasqueradePageObject
from selenium_tests.lti_emailer.page_objects.emailer_mainpage_page_object \
    import EmailerMainPage
from canvas_sdk.methods.external_tools \
    import (get_single_external_tool_courses,
            create_external_tool_courses,
            delete_external_tool_courses)
from canvas_sdk.exceptions import CanvasAPIError
from icommons_common.canvas_utils import SessionInactivityExpirationRC

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)
logging.basicConfig()
CANVAS_ADD_USERS = join(dirname(abspath(__file__)),
                        'test_data', 'roles_access.xlsx')
CANVAS_ROLES = join(dirname(abspath(__file__)),
                    'test_data', 'roles.xlsx')


class EmailerBaseTestCase(BaseSeleniumTestCase):
    """Emailer base test case, all other tests will subclass this class"""

    @classmethod
    def setUpClass(cls):
        """
        setup values for the tests
        """
        super(EmailerBaseTestCase, cls).setUpClass()

        tool_does_not_exist = False

        driver = cls.driver

        ## create new tool id if it does not exist
        cls.new_external_id = 0

        cls.USERNAME = settings.SELENIUM_CONFIG.get('selenium_username')
        cls.PASSWORD = settings.SELENIUM_CONFIG.get('selenium_password')
        cls.CANVAS_BASE_URL = settings.SELENIUM_CONFIG.get('canvas_base_url')
        cls.TOOL_RELATIVE_URL = settings.SELENIUM_CONFIG.get(
            'emailer_tool_relative_url')
        cls.TOOL_URL_BASE_RELATIVE = urljoin(cls.CANVAS_BASE_URL,
                                             cls.TOOL_RELATIVE_URL)
        cls.EXTERNAL_TOOL_ID = settings.SELENIUM_CONFIG.get('emailer_tool_id')
        cls.COURSE_ID = settings.SELENIUM_CONFIG.get('emailer_course_id')
        cls.masquerade_page = CanvasMasqueradePageObject(driver,
                                                         cls.CANVAS_BASE_URL)

        ### Verify that the tool_id exist
        try:
            resp= get_single_external_tool_courses(
                SDK_CONTEXT,
                course_id=cls.COURSE_ID,
                external_tool_id=cls.EXTERNAL_TOOL_ID)
            logger.debug("Successful tool lookup:".format(resp))
        except CanvasAPIError as api_error:
            tool_does_not_exist = True
            logger.error(
                "CanvasAPIError in retrieving the external tool id %s "
                "from course %s. Exception=%s:",
                cls.EXTERNAL_TOOL_ID, cls.COURSE_ID, api_error
            )

        ## if the tool does not exist, go ahead and add the tool to the course
        if tool_does_not_exist:

            name='Emailer Tool Dev Selenium Automation'
            domain="lti-emailer.dev.tlt.harvard.edu"
            config_url='http://lti-emailer.dev.tlt.harvard.edu/tool_config'

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
                new_external_tool_resp = create_external_tool_courses(
                    **request_parameters)
                logger.debug(
                    "Successful Create:".format(new_external_tool_resp))
                new_course_json = new_external_tool_resp.json()
                cls.new_external_id = new_course_json['id']
                cls.EXTERNAL_TOOL_ID = str(cls.new_external_id)
            except CanvasAPIError as api_error:
                logger.exception(
                    'Error building request_parameters or executing '
                    'create_external_tool_courses() '
                    'SDK call for new external tool with request=%s: '
                    'for course %s. Exception=%s',
                    request_parameters, cls.COURSE_ID, api_error
                )

        cls.TOOL_URL = urljoin(cls.TOOL_URL_BASE_RELATIVE,
                               cls.EXTERNAL_TOOL_ID)
        cls.emailer_main_page = EmailerMainPage(driver)
        cls.emailer_main_page.get(cls.TOOL_URL)
        login_page = PinLoginPageObject(driver)
        if login_page.is_loaded():
            login_page.login_xid(cls.USERNAME, cls.PASSWORD)
        else:
            print('(User {} already logged in to PIN)'.format(cls.USERNAME))

    @classmethod
    def tearDownClass(cls):
        super(EmailerBaseTestCase, cls).tearDownClass()

        ## Only delete new external tool id, if original external id
        ## does not exist
        if cls.new_external_id > 0:
            try:
                resp = delete_external_tool_courses(
                    SDK_CONTEXT,
                    course_id=cls.COURSE_ID,
                    external_tool_id=cls.EXTERNAL_TOOL_ID)
                logger.debug("Successful Delete:".format(resp))
            except CanvasAPIError as api_error:
                logger.error(
                    "CanvasAPIError in deleting the external tool id %s "
                    "from course %s. Exception=%s:",
                    cls.EXTERNAL_TOOL_ID, cls.COURSE_ID, api_error
                )
