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

from mailgun.decorators import authenticate
from mailgun.route_handlers import handle_mailing_list_email_route


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
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
