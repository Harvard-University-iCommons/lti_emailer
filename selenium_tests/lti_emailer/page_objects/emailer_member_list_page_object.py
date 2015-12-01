from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base_page_object import EmailerBasePageObject

class EmailerMainPageLocators(object):
    PAGE_TITLE = (By.CSS_SELECTOR, "h1")


class CourseEmailerListPage(EmailerBasePageObject):

    def is_loaded(self):
        """
        Verifies that the page is loaded correctly by validating the title
        :returns True if title matches else a RuntimeError is raised
        """
        # Note: this just checks that the  title is displayed;
        # it doesn't guaranteed that everything we expect is rendered on the
        # page, because angular fetches the data asynchronously

        title = None
        try:
            title = self.get_page_title()
        except NoSuchElementException:
            return False

        if title and 'Course Emailer' in title.get_attribute('textContent'):
            return True
        else:
            raise RuntimeError(
                'Could not determine if dashboard page loaded as expected;'
                'title element was found but did not contain expected text'
            )
