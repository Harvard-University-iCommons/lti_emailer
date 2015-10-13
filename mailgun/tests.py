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

from mock import MagicMock, call, patch

from icommons_common.utils import Bunch

from mailgun.decorators import authenticate
from mailgun.route_handlers import handle_mailing_list_email_route


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
class RouteHandlerUnitTests(TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='unittest',
                                             email='unittest@example.edu',
                                             password='unittest')

    @override_settings(CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT='%s:%s')
    @patch('mailgun.route_handlers.cache.get')
    @patch('mailgun.route_handlers.CourseInstance.objects.get')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_duplicate_router_post(self, mock_ml_get, mock_ci_get, mock_cache_get):
        ''' TLT-2039
        Verifies that if a message-id is in the cache, we won't try to send
        that email to the list again.
        '''
        # only the message-id is needed
        post_body = {
            'Message-Id': uuid.uuid4().hex,
            'sender': 'tlttest52@gmail.com',
            'recipient': 'tlttest53@gmail.com'
        }
        post_body.update(generate_signature_dict())

        # the message-id is in the cache
        mock_cache_get.return_value = True

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)

        # verify cache.get we're expecting, and other mocks unused
        self.assertEqual(mock_cache_get.call_args,
                         call("%s:%s" % (post_body['Message-Id'], post_body['recipient'])))
        self.assertEqual(mock_ml_get.call_count, 0)
        self.assertEqual(mock_ci_get.call_count, 0)


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
        members = [{'address': a} for a in ['unittest@example.edu', 'student@example.edu']]
        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher@example.edu'},
            members=members,
            address='class-list@example.edu'
        )
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

    @patch('mailgun.route_handlers.CourseInstance.objects.get')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_multi_mailing_list_recipients(self, mock_ml_get, mock_ci_get):
        '''
        TLT-2066
        Verifies that we can handle route handler POSTs that have multiple mailing list addresses in the recipient
        request param
        '''
        # prep a MailingList mock
        members = [{'address': a} for a in ['unittest@example.edu', 'student@example.edu']]
        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher@example.edu'},
            members=members,
            address='class-list@example.edu'
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners')
        mock_ci_get.return_value = ci

        # prep the post body
        recipients = ', '.join([ml.address, 'bogus@example.edu'])
        post_body = {
            'sender': 'Unit Test <unittest@example.edu>',
            'recipient': recipients,
            'subject': 'blah',
            'body-plain': 'blah blah',
            'To': recipients
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)
        send_mail_call = call(
            'Unit Test via Canvas',
            'unittest@example.edu',
            ['teacher@example.edu', 'student@example.edu'],
            '[Lorem For Beginners] blah',
            attachments=[],
            html='',
            inlines=[],
            message_id=None,
            original_cc_address=[],
            original_to_address=['class-list@example.edu', 'bogus@example.edu'],
            text='blah blah'
        )
        ml.send_mail.assert_has_calls([send_mail_call, send_mail_call])


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
