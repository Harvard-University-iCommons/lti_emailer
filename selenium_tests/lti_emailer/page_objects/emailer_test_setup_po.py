from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium_tests.lti_emailer.page_objects.emailer_base_page import EmailerBasePage

from django.conf import settings


class EmailerTestSetupLocators(object):

    """These are page-specific locators on the Canvas' Add People Page"""

    _add_people_url = '%s/courses/6389/users' % settings.SELENIUM_CONFIG.get('base_url')
    _switchframe = (By.ID, "tool_content")
    _add_user_button = (By.ID, "addUsers")
    _addtextarea = (By.ID, "user_list_textarea")
    _next_button = (By.ID, "next-step")
    _create_user = (By.ID, "createUsersAddButton")
    _confirm_create = (By.XPATH, "//button[@type='button']")
    _canvas_role = (By.ID, "role_id")


class EmailerTestSetupPO(EmailerBasePage):

    def add_users(self, user_id, roles):
        """Goes to Canvas Add People URL and adds user"""
        driver = self._driver
        driver.get(EmailerTestSetupLocators._add_people_url)
        driver.find_element(*EmailerTestSetupLocators._add_user_button).click()
        driver.find_element(*EmailerTestSetupLocators._addtextarea).clear()
        send_userid = driver.find_element(*EmailerTestSetupLocators._addtextarea)
        send_userid.send_keys(user_id)
        Select(driver.find_element(*EmailerTestSetupLocators._canvas_role)).select_by_visible_text(roles)

    def confirm_add(self):
        """Confirms user add"""
        driver = self._driver
        driver.find_element(*EmailerTestSetupLocators._next_button).click()
        driver.find_element(*EmailerTestSetupLocators._create_user).click()
        driver.find_element(*EmailerTestSetupLocators._confirm_create).click()