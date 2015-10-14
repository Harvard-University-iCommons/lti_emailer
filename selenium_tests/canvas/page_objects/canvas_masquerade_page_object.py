from selenium.webdriver.common.by import By
from selenium_tests.canvas.page_objects.canvas_base_page_object import CanvasBasePageObject
from urlparse import urljoin


class CanvasMasqueradePageLocators(object):
    CONFIRM_BUTTON = (By.CSS_SELECTOR, "a.btn.masquerade_button")
    MASQUERADE_URL = 'users/{}/masquerade'


class CanvasMasqueradePageObject(CanvasBasePageObject):

    def __init__(self, driver, canvas_base_url=None):
        if canvas_base_url:
            self.canvas_base_url = canvas_base_url
        else:
            raise RuntimeError(
                'CanvasMasqueradePageObject must be initialized with the '
                'Selenium webdriver and the Canvas base URL; missing Canvas '
                'base URL'
            )
        super(CanvasMasqueradePageObject, self).__init__(driver)

    def masquerade_as(self, canvas_user_id):
        relative_url = CanvasMasqueradePageLocators.MASQUERADE_URL.format(canvas_user_id)
        full_url = urljoin(self.canvas_base_url, relative_url)
        self._driver.get(full_url)
        return self

    def confirm_masquerade(self):
        confirm_button = self.find_element(
            *CanvasMasqueradePageLocators.CONFIRM_BUTTON
        )
        confirm_button.click()
        return self
