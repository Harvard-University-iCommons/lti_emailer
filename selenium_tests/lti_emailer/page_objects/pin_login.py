from selenium_tests.lti_emailer.page_objects.pin_login_page_object import PinLoginPageObject

class PinLogin(PinLoginPageObject):

    def login(self, username, password):
        """
        override the login method to return the correct page object.
        note that super must be called to do the actual login.
        """
        super(PinLogin, self).login(username, password)
        print 'Pin Login page returning Index page for user: %s' % username