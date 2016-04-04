from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base_page_object import EmailerBasePageObject


class EmailerMainPageLocators(object):
    UNAUTHORIZED_MESSAGE = (By.ID, "unauthorized_message")
    MEMBER_LINK = (By.PARTIAL_LINK_TEXT, "members")
    MAILING_LISTS_ID = (By.ID, "course-mailing-lists")

class EmailerMainPage(EmailerBasePageObject):
    page_loaded_locator = EmailerMainPageLocators.MAILING_LISTS_ID

    def is_authorized(self):

        try:
            self.find_element(*EmailerMainPageLocators.UNAUTHORIZED_MESSAGE)
        except NoSuchElementException:

            #unauthorized message not found, we should see main page header
            return True

        # we found the unauthorized message, so we're explicitly unauthorized
        return False

    def get_member_link(self):
        element = self.find_element(*EmailerMainPageLocators.MEMBER_LINK)
        return element

    def select_member_link(self):
        """
        select the course info link element and click it
        """
        self.find_element(*EmailerMainPageLocators.MEMBER_LINK).click()
