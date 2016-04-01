from ddt import ddt, data, unpack

from selenium_common.base_test_case import get_xl_data
from selenium_tests.lti_emailer.emailer_base_test_case import CANVAS_ADD_USERS
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

        self.masquerade_page.masquerade_as(user_id)
        self.emailer_main_page.get(self.TOOL_URL)
        if given_access == 'no':
            self.assertFalse(
                self.emailer_main_page.is_authorized(),
                'User {} has been authorized, '
                'but should not be.'.format(user_id)
            )

        elif given_access == 'yes':
            self.assertTrue(
                self.emailer_main_page.is_authorized(),
                'User {} not authorized, but should be.'.format(user_id)
            )

        else:
            raise ValueError(
                'given_access column for user {} must be either \'yes\' or '
                '\'no\''.format(user_id)
            )
