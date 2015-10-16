from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base_page_object import EmailerBasePageObject

class EmailerMainPageLocators(object):
    PAGE_TITLE = (By.CSS_SELECTOR, "h1")
    UNAUTHORIZED_MESSAGE = (By.ID, "unauthorized_message")


class EmailerMainPage(EmailerBasePageObject):

    def is_authorized(self):
        # frame context stickiness is a bit flaky for some reason, so make sure
        # we're in the tool_content frame context before checking for elements
        self.focus_on_tool_frame()
        # todo: this would be quicker if we can look for a specific indication
        #       of authorized, e.g. check is_loaded() before
        #       UNAUTHORIZED_MESSAGE
        try:
            self.find_element(*EmailerMainPageLocators.UNAUTHORIZED_MESSAGE)
        except NoSuchElementException:

            #unauthorized message not found, we should see main page header

            if self.is_loaded():
                return True
            else:
                raise RuntimeError(
                    'Could not determine if user was authorized to access '
                    'Emailer main page: no unauthorized message, but page '
                    'not loaded as expected.'
                )

        # we found the unauthorized message, so we're explicitly unauthorized
        return False

    def is_loaded(self):
        # Note: this just checks that the breadcrumb title is displayed;
        # it doesn't guaranteed that everything we expect is rendered on the
        # page, because angular fetches the data asynchronously

        # frame context stickiness is a bit flaky for some reason, so make sure
        # we're in the tool_content frame context before checking for elements
        self.focus_on_tool_frame()
        title = None
        try:
            title = self.find_element(*EmailerMainPageLocators.PAGE_TITLE)
        except NoSuchElementException:
            return False

        if title and 'Course Emailer' in title.get_attribute('textContent'):
            return True
        else:
            raise RuntimeError(
                'Could not determine if Emailer main page loaded as expected;'
                'title element was found but did not contain expected text'
            )
