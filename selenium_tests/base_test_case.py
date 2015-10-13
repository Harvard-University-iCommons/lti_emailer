import unittest
import xlrd
from pyvirtualdisplay import Display
from django.conf import settings

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


# Enabling stdout logging only for high `-v`
class BaseSeleniumTestCase(unittest.TestCase):
    driver = None  # make selenium driver available to any part of the test case
    display = None  # a reference to the virtual display (for running tests locally)

    @classmethod
    def setUpClass(cls):
        """
        Sets up the test case, including the selenium browser driver to use
        """

        local = settings.SELENIUM_CONFIG.get('run_locally', False)

        if local:
            # Run selenium tests from a headless browser within the VM
            print "\nSetting up selenium testing locally..."
            # set up virtual display
            cls.display = Display(visible=0, size=(1480, 1024)).start()
            # create a new local browser session
            # todo: browser should be configurable (i.e. not always FF)
            cls.driver = webdriver.Firefox()
        else:
            # Run selenium tests from the Selenium Grid server
            selenium_grid_url = settings.SELENIUM_CONFIG.get('selenium_grid_url', None)
            if selenium_grid_url:
                cls.driver = webdriver.Remote(
                    command_executor=selenium_grid_url,
                    desired_capabilities=DesiredCapabilities.FIREFOX
                )
            else:
                raise ValueError(
                    "Selenium grid url needs to be specified in the project "
                    "settings to use remote webdriver, or you can run the "
                    "selenium tests locally by setting the run_locally "
                    "project setting instead."
                )

        # shared defaults
        cls.driver.implicitly_wait(10)
        cls.driver.maximize_window()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        if cls.display:
            cls.display.stop()


def get_xl_data(file_name, sheet_index=0, header_row=True):
    # create an empty list to store rows Using Excel
    rows = []
    # open the specified Excel spreadsheet as workbook
    book = xlrd.open_workbook(file_name)
    # get the first sheet
    sheet = book.sheet_by_index(sheet_index)
    # iterate through the sheet and get data from rows in list
    start_row_index = 1 if header_row else 0
    for row_idx in range(start_row_index, sheet.nrows):
        rows.append(list(sheet.row_values(row_idx, 0, sheet.ncols)))
    return rows




