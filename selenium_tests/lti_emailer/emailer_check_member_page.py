from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase

class CheckMemberPage(EmailerBaseTestCase):

    def test_member_page_loaded(self):
        emailer_main_page = self.emailer_main_page
        course_emailer_page = emailer_main_page.select_member_link()
        self.assertTrue(course_emailer_page.is_loaded())
