from selenium.common.exceptions import NoSuchElementException
from selenium_common.base_page_object import BasePageObject


# This is the base class that all page models can inherit from
class EmailerBasePageObject(BasePageObject):

    def __init__(self, driver):
        super(EmailerBasePageObject, self).__init__(driver)
        try:
            self.focus_on_tool_frame()
        except NoSuchElementException:
            pass

    def open(self, url):
        self._driver.get(url)
        return self
