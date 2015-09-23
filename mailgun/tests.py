import json
import hashlib
import hmac
import json
import time
import uuid
from StringIO import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from mock import MagicMock, patch

from icommons_common.utils import Bunch

from lti_emailer.exceptions import ListservApiError
from mailing_list.models import MailingList
from .listserv_client import MailgunClient as ListservClient
from .decorators import authenticate
from .route_handlers import handle_mailing_list_email_route


class RouteHandlerRegressionTests(TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='unittest',
                                             email='unittest@example.edu',
                                             password='unittest')

    @patch('mailgun.route_handlers.CourseInstance.objects.get')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_empty_body_html(self, mock_ml_get, mock_ci_get):
        ''' TLT-2006
        Verifies that we can handle emails that
        * have at least one inlined attachment
        * do not have an html body
        '''
        # prep an attachment object (attributes added to match what
        # django.test.client.encode_file() looks for)
        attachment_fp = StringIO('lorem ipsum')
        attachment_fp.name = 'lorem.txt'
        attachment_fp.content_type = 'text/plain'

        # prep a MailingList mock
        members = [{'address': a} for a in
                       ['unittest@example.edu', 'student@example.edu']]
        ml = MagicMock(
                canvas_course_id=123,
                section_id=456,
                teaching_staff_addresses={'teacher@example.edu'},
                members=members,
                address='class-list@example.edu')
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners')
        mock_ci_get.return_value = ci

        # prep the post body
        post_body = {
            'sender': 'Unit Test <unittest@example.edu>',
            'recipient': ml.address,
            'subject': 'blah',
            'body-plain': 'blah [cid:{}] blah'.format(attachment_fp.name),
            'To': ml.address,
            'attachment-count': 1,
            'attachment-1': attachment_fp,
            'content-id-map': json.dumps({attachment_fp.name: 'attachment-1'}),
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)


class ListservClientTests(TestCase):
    fixtures = [
        'mailing_list/fixtures/test_mailing_list.json'
    ]
    longMessage = True

    @patch('requests.get')
    def test_get_list_success(self, mock_requests_get):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200,
            json=lambda: {'list': {}}
        )
        mock_requests_get.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)

        result = listserv_client.get_list(mailing_list)

        mock_requests_get.assert_called_with(api_url, auth=auth)
        self.assertEqual(result, {})

    @patch('requests.get')
    def test_get_list_not_found(self, mock_requests_get):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=404,
            json=lambda: {}
        )
        mock_requests_get.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)

        result = listserv_client.get_list(mailing_list)

        mock_requests_get.assert_called_with(api_url, auth=auth)
        self.assertIsNone(result)

    @patch('requests.get')
    def test_get_list_exception(self, mock_requests_get):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Call to get_list failed."
        )
        mock_requests_get.return_value = response
        mailing_list = MailingList.objects.get(id=1)

        with self.assertRaises(ListservApiError):
            listserv_client.get_list(mailing_list)

    @patch('requests.post')
    def test_create_list_success(self, mock_requests_post):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200
        )
        mock_requests_post.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists" % settings.LISTSERV_API_URL
        auth = (listserv_client.api_user, listserv_client.api_key)
        payload = {
            'address': mailing_list.address,
            'access_level': 'readonly'
        }

        listserv_client.create_list(mailing_list)

        mock_requests_post.assert_called_with(api_url, auth=auth, data=payload)

    @patch('requests.post')
    def test_create_list_exception(self, mock_requests_post):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Call to create_list failed."
        )
        mock_requests_post.return_value = response
        mailing_list = MailingList.objects.get(id=1)

        with self.assertRaises(ListservApiError):
            listserv_client.create_list(mailing_list)

    @patch('requests.delete')
    def test_delete_list_success(self, mock_requests_delete):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200
        )
        mock_requests_delete.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)

        result = listserv_client.delete_list(mailing_list)

        mock_requests_delete.assert_called_with(api_url, auth=auth)

    @patch('requests.delete')
    def test_delete_list_exception(self, mock_requests_delete):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Call to delete_list failed."
        )
        mock_requests_delete.return_value = response
        mailing_list = MailingList.objects.get(id=1)

        with self.assertRaises(ListservApiError):
            listserv_client.delete_list(mailing_list)

    @patch('requests.put')
    def test_update_list_success(self, mock_requests_put):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200
        )
        mock_requests_put.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)
        payload = {
            'access_level': 'members'
        }

        listserv_client.update_list(mailing_list)

        mock_requests_put.assert_called_with(api_url, auth=auth, data=payload)

    @patch('requests.put')
    def test_update_list_exception(self, mock_requests_put):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Failed to update list."
        )
        mock_requests_put.return_value = response
        mailing_list = MailingList.objects.get(id=1)

        with self.assertRaises(ListservApiError):
            listserv_client.update_list(mailing_list)

    @patch('requests.get')
    def test_members_success(self, mock_requests_get):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200,
            json=lambda: {'items': [], 'total_count': 0}
        )
        mock_requests_get.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s/members?limit=100&skip=0" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)

        result = listserv_client.members(mailing_list)

        mock_requests_get.assert_called_with(api_url, auth=auth)
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_members_exception(self, mock_requests_get):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Failed to get members."
        )
        mock_requests_get.return_value = response
        mailing_list = MailingList.objects.get(id=1)

        with self.assertRaises(ListservApiError):
            listserv_client.members(mailing_list)

    @patch('requests.post')
    def test_add_members_success(self, mock_requests_post):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200
        )
        mock_requests_post.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        api_url = "%slists/%s/members.json" % (settings.LISTSERV_API_URL, mailing_list.address)
        auth = (listserv_client.api_user, listserv_client.api_key)
        emails = ['douglas_hall@harvard.edu', 'david_bonner@harvard.edu']
        payload = {
            'members': json.dumps(emails),
            'upsert': 'yes'
        }

        listserv_client.add_members(mailing_list, emails)

        mock_requests_post.assert_called_with(api_url, auth=auth, data=payload)

    @patch('requests.post')
    def test_add_members_exception(self, mock_requests_post):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Failed to add members."
        )
        mock_requests_post.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        emails = ['douglas_hall@harvard.edu', 'david_bonner@harvard.edu']

        with self.assertRaises(ListservApiError):
            listserv_client.add_members(mailing_list, emails)

    @patch('requests.delete')
    def test_delete_members_success(self, mock_requests_delete):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=200
        )
        mock_requests_delete.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        emails = ['douglas_hall@harvard.edu']
        api_url = "%slists/%s/members/%s" % (settings.LISTSERV_API_URL, mailing_list.address, emails[0])
        auth = (listserv_client.api_user, listserv_client.api_key)

        listserv_client.delete_members(mailing_list, emails)

        mock_requests_delete.assert_called_with(api_url, auth=auth)

    @patch('requests.delete')
    def test_delete_members_exception(self, mock_requests_delete):
        listserv_client = ListservClient()
        response = Bunch(
            status_code=500,
            text="Failed to delete members."
        )
        mock_requests_delete.return_value = response
        mailing_list = MailingList.objects.get(id=1)
        emails = ['douglas_hall@harvard.edu']

        with self.assertRaises(ListservApiError):
            listserv_client.delete_members(mailing_list, emails)


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
class DecoratorTests(TestCase):
    longMessage = True

    def setUp(self):
        self.POST = generate_signature_dict()

    def test_authenticate_success(self):
        request = Bunch(
            POST=self.POST
        )
        view = MagicMock(return_value='fake response')
        decorated = authenticate()(view)
        response = decorated(request)
        view.assert_called_with(request)

    @patch('mailgun.decorators.redirect')
    def _test_authenticate_failure(self, request_post, mock_redirect):
        request = Bunch(
            POST=request_post
        )
        view = MagicMock(return_value='fake response')
        decorated = authenticate()(view)
        response = decorated(request)
        mock_redirect.assert_called_with(reverse_lazy('mailgun:auth_error'))

    @patch('mailgun.decorators.redirect')
    def test_authenticate_missing_timestamp(self, mock_redirect):
        self._test_authenticate_failure({
            'token': self.POST['token'],
            'signature': self.POST['signature']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_stale_timestamp(self, mock_redirect):
        timestamp = str(time.time() - 2 * settings.MAILGUN_CALLBACK_TIMEOUT)
        self._test_authenticate_failure({
            'timestamp': timestamp,
            'token': self.POST['token'],
            'signature': self.POST['signature']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_missing_token(self, mock_redirect):
        self._test_authenticate_failure({
            'timestamp': self.POST['timestamp'],
            'signature': self.POST['signature']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_missing_signature(self, mock_redirect):
        self._test_authenticate_failure({
            'timestamp': self.POST['timestamp'],
            'token': self.POST['token']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_bad_timestamp(self, mock_redirect):
        self._test_authenticate_failure({
            'timestamp': '0',
            'token': self.POST['token'],
            'signature': self.POST['signature']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_bad_token(self, mock_redirect):
        self._test_authenticate_failure({
            'timestamp': self.POST['timestamp'],
            'token': 'FFFF',
            'signature': self.POST['signature']
        })

    @patch('mailgun.decorators.redirect')
    def test_authenticate_bad_signature(self, mock_redirect):
        self._test_authenticate_failure({
            'timestamp': self.POST['timestamp'],
            'token': self.POST['token'],
            'signature': 'FFFF'
        })


def generate_signature_dict():
    timestamp = str(time.time())
    token = str(uuid.uuid4())
    signature = hmac.new(
        key=settings.LISTSERV_API_KEY,
        msg='{}{}'.format(timestamp, token),
        digestmod=hashlib.sha256
    ).hexdigest()
    return {
        'timestamp': timestamp,
        'token': token,
        'signature': signature
    }
