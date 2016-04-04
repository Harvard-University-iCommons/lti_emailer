from selenium_tests.lti_emailer.emailer_base_test_case import EmailerBaseTestCase
from selenium_tests.lti_emailer.page_objects.emailer_member_list_page_object import CourseEmailerListPage

class CheckMemberPage(EmailerBaseTestCase):

    def test_member_page_loaded(self):
        emailer_main_page = self.emailer_main_page
        course_emailer_page = CourseEmailerListPage(self.driver)
        emailer_main_page.select_member_link()
        self.assertTrue(course_emailer_page.is_loaded())
