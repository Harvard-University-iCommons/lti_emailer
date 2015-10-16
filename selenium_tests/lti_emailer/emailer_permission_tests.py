import unittest

from ddt import ddt, data, unpack

from selenium_tests.base_test_case import get_xl_data
from selenium_tests.lti_emailer.emailer_base_test_case import CANVAS_ADD_USERS
from selenium_tests.lti_emailer.masquerade.canvas_masquerade_page_object import \
    CanvasMasqueradePageObject
from selenium_tests.lti_emailer.emailer_base_test_case import \
    EmailerBaseTestCase


@ddt
class EmailerPermissionTests(EmailerBaseTestCase):
    @data(*get_xl_data(CANVAS_ADD_USERS))
    @unpack
    def test_roles_access(self, user_id, given_access):
        # This test masquerades as users in roles specified defined in
        # CANVAS_ADD_USERS (Excel spreadsheet) then validates if the users
        # are granted/denied access based on their role.

        emailer_main_page = self.emailer_main_page
        masquerade_page = CanvasMasqueradePageObject(self.driver, self.CANVAS_BASE_URL)
        masquerade_page.masquerade_as(user_id)
        emailer_main_page.get(self.TOOL_URL)
        if given_access == 'no':
            self.assertFalse(
                emailer_main_page.is_authorized(),
                'User {} unexpectedly authorized'.format(user_id)
            )

        elif given_access == 'yes':
            self.assertTrue(
                emailer_main_page.is_authorized(),
                'User {} not authorized as expected'.format(user_id)
            )

        else:
            raise ValueError(
                'given_access column for user {} must be either \'yes\' or '
                '\'no\''.format(user_id)
            )

if __name__ == "__main__":
    unittest.main()