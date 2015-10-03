__author__ = 'hic048'

from selenium.webdriver.common.by import By
from selenium_tests.lti_emailer.page_objects.emailer_base import EmailerBasePage
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select

# These are page-specific locators.
class Locator3(object):
      _add_people_url = "http://canvas.icommons.harvard.edu/courses/6389/users"
      _switchframe = (By.ID, "tool_content")
      _add_user_button = (By.ID, "addUsers")
      _addtextarea = (By.ID, "user_list_textarea")
      _next_button = (By.ID, "next-step")
      _create_user = (By.ID, "createUsersAddButton")
      _confirm_create = (By.XPATH, "//button[@type='button']")
      _canvas_role = (By.ID, "role_id")



class UserAdd(EmailerBasePage):

    def switch_frame(self):
        driver = self._driver
        driver.switch_to.frame(driver.find_element(*Locator3._switchframe))

    def find_user_add (self):
        driver = self._driver
        driver.get(Locator3._add_people_url)
        self.find_element(*Locator3._add_user_button).click()
        self.find_element(*Locator3._addtextarea).clear()


    def confirm_add(self):
        driver = self._driver
        self.find_element(*Locator3._next_button).click()
        self.find_element(*Locator3._create_user).click()
        self.find_element(*Locator3._confirm_create).click()





