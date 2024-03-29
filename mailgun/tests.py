import hashlib
import hmac
import json
import time
import uuid
from io import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from mock import MagicMock, call, patch

from harvard_django_utils.utils import Bunch

from mailing_list.models import MailingList
from mailgun.decorators import authenticate
from mailgun.exceptions import HttpResponseException
from mailgun.route_handlers import (
    CommChannelCache,
    handle_mailing_list_email_route)


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
class RouteHandlerUnitTests(TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='unittest@example.edu',
                                             password='insecure',
                                             username='unittest')
        self.user.first_name = 'Unit'
        self.user.last_name = 'Test'

    @override_settings(CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT='%s:%s')
    @patch('mailgun.route_handlers.cache.get')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
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
        expected_cache_key = (
            settings.CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT
            % (post_body['Message-Id'], post_body['recipient']))
        self.assertEqual(mock_cache_get.call_args, call(expected_cache_key))
        self.assertEqual(mock_ml_get.call_count, 0)
        self.assertEqual(mock_ci_get.call_count, 0)

    @patch('mailgun.route_handlers.logger.exception')
    @patch('mailgun.route_handlers._handle_recipient')
    def test_unhandled_exception(self, mock_handle_recipient, mock_log_exc):
        '''
        TLT-2130: Should log mailgun POST on unhandled exception
        '''

        # mock an unhandled error in the method that sends mail to a recipient
        mock_handle_recipient.side_effect = RuntimeError()

        post_body = {
            'recipient': 'class-list@example.edu',
            'sender': 'Unit Test <unittest@example.edu>',
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        response = handle_mailing_list_email_route(request)

        # expecting server error
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b'{"success": false}')

        # verify we logged post data
        self.assertEqual(mock_log_exc.call_count, 1)
        logger_post_info = mock_log_exc.call_args[0][1]  # second positional arg
        self.assertEqual(json.dumps(post_body, sort_keys=True), logger_post_info)

    @patch('mailgun.route_handlers.logger.exception')
    @patch('mailgun.route_handlers._handle_recipient')
    def test_response_exception(self, mock_handle_recipient, mock_log_exc):
        '''
        TLT-2108: We sometimes need to return a non-200 response, and we don't
        always want to return a 500.  Raising a JsonExceptionResponse from
        somewhere in the stack should result in that response being returned to
        Mailgun.
        '''
        raised_response = JsonResponse(
                              {'message': "I'm a teapot!"}, status=418)
        mock_handle_recipient.side_effect = HttpResponseException(raised_response)

        post_body = {
            'recipient': 'class-list@example.edu',
            'sender': 'Unit Test <unittest@example.edu>',
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        response = handle_mailing_list_email_route(request)

        # expecting the response we raised
        self.assertEqual(response.status_code, raised_response.status_code)
        self.assertEqual(response.content, raised_response.content)

        # verify we logged post data
        self.assertEqual(mock_log_exc.call_count, 1)
        logger_post_info = mock_log_exc.call_args[0][2]  # third positional arg
        self.assertEqual(json.dumps(post_body, sort_keys=True), logger_post_info)

    @patch('mailgun.route_handlers.logger.exception')
    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_missing_attachment(self, mock_ml_get, mock_ci_get, mock_ss_filter, mock_log_exc):
        '''
        TLT-2108: If an attachment is missing from a POST, we should return a
        400 and log it.
        '''
        # prep a MailingList mock
        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses=set(),
            members=[],
            address='class-list@example.edu'
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

        # prep the post body
        post_body = {
            'sender': self.user.email,
            'recipient': ml.address,
            'subject': 'test missing attachment',
            'body-plain': 'blah blah',
            'To': ml.address,
            'attachment-count': '1',
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        response = handle_mailing_list_email_route(request)

        # make sure we got a 400 response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content),
                         {
                             'message': 'Attachment attachment-1 missing from POST',
                             'success': False,
                         })

        # verify we logged post data and a reason
        self.assertEqual(mock_log_exc.call_count, 2)
        missing_attachment_call = mock_log_exc.call_args_list[0]
        self.assertEqual(missing_attachment_call[0][0], # positional arg
                         'Mailgun POST claimed to have %s attachments, but %s '
                         'is missing')
        log_the_post_call = mock_log_exc.call_args_list[1]
        self.assertEqual(json.loads(log_the_post_call[0][-1]), post_body)


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
class RouteHandlerAccessTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super(RouteHandlerAccessTests, cls).setUpClass()

        # craft a POST request
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            email='unittest@example.edu',
            password='insecure',
            username='unittest')
        cls.user.first_name = 'Unit'
        cls.user.last_name = 'Test'

        # set up some defaults used when generating mocks for each test case
        cls.regular_member_address = 'student@example.edu'
        cls.staff_member_address = 'teacher@example.edu'
        cls.members = [{'address': a} for a in
                        ['unittest@example.edu', cls.regular_member_address]]

    def setUp(self):
        super(RouteHandlerAccessTests, self).setUp()
        self._setup_mocks()

    def _setup_mocks(self):
        """
        set up each test case so it has a fresh set of mocks that it can
        override as needed
        """

        # create mock objects with the required defaults
        self.alt_emails = []
        self.ml_mock = self._get_ml_mock()
        self.ci_mock = self._get_ci_mock()  # depends on self.ml_mock

        # create fake request
        self.post_body = self._get_post_body()  # depends on self.ml_mock

        # patch the target methods with the mocks we created above
        self.mock_get_alt_emails = self._create_patch(
            'mailgun.route_handlers.CommChannelCache.get_for')
        self.mock_get_alt_emails.return_value = self.alt_emails
        self.mock_get_ci = self._create_patch(
            'mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
        self.mock_get_ci.return_value = self.ci_mock
        self.mock_get_ml = self._create_patch(
            'mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
        self.mock_get_ml.return_value = self.ml_mock

        # patch target methods that don't need defaults
        self.mock_send_bounce = self._create_patch(
            'mailgun.route_handlers._send_bounce')
        self.mock_ss = self._create_patch(
            'mailgun.route_handlers.SuperSender.objects.filter')

    def _create_patch(self, name):
        patcher = patch(name)
        thing = patcher.start()
        # need this in case test fails unexpectedly
        self.addCleanup(patcher.stop)
        return thing

    def _get_ci_mock(self):
        return MagicMock(
            canvas_course_id=self.ml_mock.canvas_course_id,
            course_instance_id=789,
            course=MagicMock(school_id='colgsas'),
            short_title='Lorem For Beginners')

    def _get_ml_mock(self):
        return MagicMock(
            address='class-list@example.edu',
            canvas_course_id=123,
            members=self.members,
            section_id=456,
            teaching_staff_addresses={self.staff_member_address})

    def _get_post_body(self):
        post_body_template = {
            'recipient': [self.ml_mock.address],
            'sender': ['Student X <{}>'.format(self.regular_member_address)],
            'subject': ['blah'],
            'To': [self.ml_mock.address]}
        post_body_template.update(generate_signature_dict())
        return post_body_template

    def _get_post_request(self):
        request = self.factory.post('/', self.post_body)
        request.user = self.user
        return request


class RouteHandlerSuperSenderTests(RouteHandlerAccessTests):
    def test_from_is_supersender_sender_is_authorized(self):
        """
        for any list type (testing readonly here), mail should be
        delivered/routed as the from address if from address is a supersender
        and sender is one of the active email addresses in the supersender's
        Canvas communication channels
        """
        send_mail_mock = self.mock_get_ml.return_value.send_mail

        alternate_email = 'alt@example.edu'
        from_display_name = 'Student'
        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_EVERYONE
        self.mock_get_alt_emails.return_value = [alternate_email]
        self.mock_ss.return_value.values_list.return_value = [self.regular_member_address]
        self.post_body['sender'] = 'Alt Email <{}>'.format(alternate_email)
        self.post_body['from'] = '{} <{}>'.format(from_display_name,
                                                  self.regular_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

        # check that first two positional args to send_mail() are what we expect
        sender_display_name = send_mail_mock.call_args[0][0]
        sender_address = send_mail_mock.call_args[0][1]
        expected_display_name = from_display_name + ' via Canvas'
        self.assertEqual(sender_display_name, expected_display_name)
        self.assertEqual(sender_address, self.regular_member_address)


class RouteHandlerPublicListTests(RouteHandlerAccessTests):
    def test_public_list(self):
        """
        senders who are not mailing list members should be able to send to a
        public mailing list
        """

        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_EVERYONE
        self.post_body['sender'] = 'Not a member <notamember@example.edu>'

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

    def test_public_list_from_is_member_sender_is_authorized(self):
        """
        for public lists, mail should be delivered/routed as the from address if
        from address is a member and sender is one of the active email addresses
        in the member's Canvas communication channels
        """
        send_mail_mock = self.mock_get_ml.return_value.send_mail

        alternate_email = 'alt@example.edu'
        from_display_name = 'Student'
        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_EVERYONE
        self.mock_get_alt_emails.return_value = [alternate_email]
        self.post_body['sender'] = 'Alt Email <{}>'.format(alternate_email)
        self.post_body['from'] = '{} <{}>'.format(from_display_name,
                                                  self.regular_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

        # check that first two positional args to send_mail() are what we expect
        sender_display_name = send_mail_mock.call_args[0][0]
        sender_address = send_mail_mock.call_args[0][1]
        expected_display_name = from_display_name + ' via Canvas'
        self.assertEqual(sender_display_name, expected_display_name)
        self.assertEqual(sender_address, self.regular_member_address)


class RouteHandlerReadOnlyListTests(RouteHandlerAccessTests):
    def test_read_only_list(self):
        """
        even staff list members should not be able to send to a read-only list
        (note, if the sender and from addresses do not match a list member, a
        more general error would be raised instead)
        """

        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_READONLY
        self.post_body['sender'] = 'Staff <{}>'.format(self.staff_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 1)

        # check that first positional arg to _send_bounce() is what we expect
        bounce_back_template_arg = self.mock_send_bounce.call_args[0][0]
        self.assertEqual(bounce_back_template_arg,
                         'mailgun/email/bounce_back_readonly_list.html')

    def test_super_senders_can_send_to_read_only_lists(self):
        """ super senders _can_ send to read-only lists """
        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_READONLY
        self.mock_ss.return_value.values_list.return_value = [self.regular_member_address]

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)


class RouteHandlerMembersOnlyListTests(RouteHandlerAccessTests):
    def test_members_list_sender_and_from_are_not_members(self):
        """
        incoming mail with sender and from addresses that do not match a list
        member should not be able to send to a members-only mailing list
        """

        self.post_body['sender'] = 'Not a member <notamember@example.edu>'

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 1)

        # check that first positional arg to _send_bounce() is what we expect
        bounce_back_template_arg = self.mock_send_bounce.call_args[0][0]
        self.assertEqual(bounce_back_template_arg,
                         'mailgun/email/bounce_back_not_subscribed.html')

    def test_members_list_sender_is_member(self):
        """
        senders who are mailing list members should be able to send to a
        members-only mailing list
        """

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)
        # no need to fetch valid email communication channels
        self.assertEqual(self.mock_get_alt_emails.call_count, 0)

    def test_members_list_from_is_member_sender_is_authorized(self):
        """
        for members-only lists, mail should be delivered/routed as the from
        address if from address is a member and sender is one of the
        active email addresses in the member's Canvas communication channels
        """
        send_mail_mock = self.mock_get_ml.return_value.send_mail

        alternate_email = 'alt@example.edu'
        from_display_name = 'Student'
        self.mock_get_alt_emails.return_value = [alternate_email]
        self.post_body['sender'] = 'Alt Email <{}>'.format(alternate_email)
        self.post_body['from'] = '{} <{}>'.format(from_display_name,
                                                  self.regular_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

        # check that first two positional args to send_mail() are what we expect
        sender_display_name = send_mail_mock.call_args[0][0]
        sender_address = send_mail_mock.call_args[0][1]
        expected_display_name = from_display_name + ' via Canvas'
        self.assertEqual(sender_display_name, expected_display_name)
        self.assertEqual(sender_address, self.regular_member_address)

    def test_members_list_from_is_member_sender_is_unauthorized(self):
        """
        for members-only or staff-only lists from address is a member and sender
        is not one of the active email addresses in the member's Canvas
        communication channels, regardless of sender membership
        """

        self.mock_get_alt_emails.return_value = ['alt@example.edu']
        # note: Teacher _is_ a valid mailing list member (part of the teaching
        # staff addresses, but since Teacher's email address is _not_ a valid
        # communication channel for the Student represented by the from address,
        # this will be rejected; the code should not fall back on checking the
        # sender address.
        self.post_body['sender'] = 'Teacher <{}>'.format(self.staff_member_address)
        self.post_body['from'] = 'Student <{}>'.format(self.regular_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 1)

        # check that first positional arg to _send_bounce() is what we expect
        bounce_back_template_arg = self.mock_send_bounce.call_args[0][0]
        self.assertEqual(bounce_back_template_arg,
                         'mailgun/email/bounce_back_no_comm_channel_match.html')


class RouteHandlerStaffOnlyListTests(RouteHandlerAccessTests):
    def test_staff_list_sender_is_member(self):
        """
        senders who are teaching staff list members should be able to send to a
        staff-only mailing list
        """

        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_STAFF
        self.post_body['sender'] = 'Staff <{}>'.format(self.staff_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

    def test_staff_list_from_is_member_sender_is_authorized(self):
        """
        for staff-only lists, mail should be delivered/routed if sender is
        not a member, from address is a teaching staff member, and sender is one
        of the active email addresses in the member's Canvas communication
        channels
        """

        send_mail_mock = self.mock_get_ml.return_value.send_mail

        alternate_email = 'alt@example.edu'
        from_display_name = 'Staff'
        self.mock_get_ml.return_value.access_level = MailingList.ACCESS_LEVEL_STAFF
        self.mock_get_alt_emails.return_value = [alternate_email]
        self.post_body['sender'] = 'Alt Email <{}>'.format(alternate_email)
        self.post_body['from'] = '{} <{}>'.format(from_display_name,
                                                  self.staff_member_address)

        response = handle_mailing_list_email_route(self._get_post_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_send_bounce.call_count, 0)

        # check that first two positional args to send_mail() are what we expect
        sender_display_name = send_mail_mock.call_args[0][0]
        sender_address = send_mail_mock.call_args[0][1]
        expected_display_name = from_display_name + ' via Canvas'
        self.assertEqual(sender_display_name, expected_display_name)
        self.assertEqual(sender_address, self.staff_member_address)


class RouteHandlerMultipleRecipientAccessTests(RouteHandlerAccessTests):
    def test_multiple_recipient_lists_use_comm_channel_caching(self):
        """
        when sender is not a member but from address is a member, we shouldn't
        be fetching Canvas data more than once for the same user to determine
        if sender is authorized for that member.
        """

        send_mail_mock = self.mock_get_ml.return_value.send_mail

        alternate_email = 'alt@example.edu'
        from_display_name = 'Student'
        self.mock_get_alt_emails.return_value = [alternate_email]

        self.post_body['sender'] = 'Alt Email <{}>'.format(alternate_email)
        self.post_body['from'] = '{} <{}>'.format(from_display_name,
                                                  self.regular_member_address)
        # two unique recipients means that we'll be running through the same
        # from/sender list authorization logic for the same twice, once for each
        # list, so we can check whether the information has been cached.
        recipients = [self.ml_mock.address, '2@example.edu']
        self.assertNotEqual(*recipients)
        self.post_body['recipient'] = [','.join(recipients)]

        response = handle_mailing_list_email_route(self._get_post_request())
        self.assertEqual(response.status_code, 200)

        self.assertEqual(send_mail_mock.call_count, 2)  # once for each list
        # caching done behind this call, tested in CommChannelCacheTests
        self.assertEqual(self.mock_get_alt_emails.call_count, 2)


class CommChannelCacheTests(TestCase):

    @patch('mailgun.route_handlers.get_alternate_emails_for_user_email')
    def test_comm_channel_caches_backend_calls(self, mock_get_alt_emails):
        """
        Multiple calls to the CommChannelCache for the same user return the
        expected result but do not result in multiple backend calls.
        """
        expected_result = ['alt@example.edu']
        mock_get_alt_emails.return_value = expected_result
        ccc = CommChannelCache()
        e_list = ['unique@example.edu', 'dupe@example.edu', 'dupe@example.edu']
        unique_emails = len(set(e_list))
        for email in e_list:
            result = ccc.get_for(email)
            self.assertEqual(result, expected_result)
        self.assertEqual(mock_get_alt_emails.call_count, unique_emails)


@override_settings(LISTSERV_API_KEY=str(uuid.uuid4()))
class RouteHandlerRegressionTests(TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='unittest@example.edu',
                                             password='insecure',
                                             username='unittest')
        self.user.first_name = 'Unit'
        self.user.last_name = 'Test'

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_empty_body_html(self, mock_ml_get, mock_ci_get, mock_ss_filter):
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
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

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

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_multi_mailing_list_recipients_with_course_settings_none(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        '''
        TLT-1943
        Verifies that always_mail_staff is set to True in course settings for the course when
        course settings in None to start. This is the default behavior, if a course settings object does not
        exist, one will be created and always_mail_staff will be set to True by default.
        request param
        '''
        # prep a MailingList mock
        members = [{'address': a} for a in ['unittest@example.edu', 'student@example.edu']]

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=None
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

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
        self.assertTrue(ml.course_settings.always_mail_staff)

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_multi_mailing_list_recipients_with_always_mail_staff_false(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        '''
        TLT-1943
        Verifies that all staff is NOT included on emails when the value of course_settings is FALSE.
        request param
        '''
        # prep a MailingList mock
        members = [{'address': a} for a in ['student@example.edu', 'unittest@example.edu']]

        cs = MagicMock(always_mail_staff=False)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher1@example.edu', 'teacher2@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

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
            ['unittest@example.edu', 'student@example.edu'],
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

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_course_list_does_not_check_section_settings(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        """
        TLT-1943
        Verifies that MailingList.course_settings.always_mail_staff is ignored
        for course lists. Couldn't find a way to patch set.union() for an object
        instance in the test method, so instead this test hacks the
        MailingList.teaching_staff_addresses to return an address which is NOT
        a member of the list itself. This is not something that would ever
        happen for a course list, because a course list is supposed to contain
        everyone in the course by definition; this is just used as a way to
        determine whether the method under test adds the teaching staff
        addresses to the final recipient list (it should not).
        """
        # prep a MailingList mock
        members = [{'address': a} for a in ['student@example.edu', 'unittest@example.edu']]

        cs = MagicMock(always_mail_staff=False)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=None,  # this signifies a full course list
            teaching_staff_addresses={'teacher1@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

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
            ['unittest@example.edu', 'student@example.edu'],
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

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_multi_mailing_list_recipients_with_always_mail_staff_true(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        '''
        TLT-2066
        Verifies that we can handle route handler POSTs that have multiple mailing list addresses in the recipient

        TLT-1943
        Verifies that all staff is included on emails when the value of course_settings is TRUE. This is the same
        behavior as the NONE value.
        request param
        '''
        # prep a MailingList mock
        members = [{'address': a} for a in ['unittest@example.edu', 'student@example.edu']]

        cs = MagicMock(always_mail_staff=True)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher1@example.edu', 'teacher2@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

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
            ['teacher1@example.edu', 'teacher2@example.edu', 'unittest@example.edu', 'student@example.edu'],
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

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_sender_receives_copy_when_always_mail_staff_false(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        """
        TLT-2960
        Verifies that when the always_mail_staff course setting is False, the
        Sender gets a copy of the email, even if they are not in the section
        """
        members = [{'address': a} for a in ['student@example.edu', 'unittest@example.edu']]
        cs = MagicMock(always_mail_staff=False)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher1@example.edu', 'teacher2@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

        # prep the post body

        # send mail to a canvas section
        recipients = (['canvas-123-456@example.edu'])
        post_body = {
            'sender': 'Unit Test <teacher1@example.edu>',
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
            'teacher1@example.edu',
            ['teacher1@example.edu', 'unittest@example.edu', 'student@example.edu'],  #sender is included in email
            '[Lorem For Beginners] blah',
            attachments=[],
            html='',
            inlines=[],
            message_id=None,
            original_cc_address=[],
            original_to_address=['canvas-123-456@example.edu'],
            text='blah blah'
        )
        ml.send_mail.assert_has_calls([send_mail_call])

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_sender_in_section_and_receives_single_mail_when_always_mail_staff_false(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        """
        TLT-2960

        Verifies that when the always_mail_staff course setting is False and the
        sender is in the section, the Sender doesn't get a duplicate email
        """
        # prep a MailingList mock
        members = [{'address': a} for a in ['teacher1@example.edu', 'unittest@example.edu', 'student@example.edu']]

        cs = MagicMock(always_mail_staff=False)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher1@example.edu', 'teacher2@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value = []

        # prep the post body

        # send mail to a canvas section
        recipients = (['canvas-123-456@example.edu'])
        post_body = {
            'sender': 'Unit Test <teacher1@example.edu>',
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
            'teacher1@example.edu',
            ['teacher1@example.edu', 'student@example.edu', 'unittest@example.edu'],
            '[Lorem For Beginners] blah',
            attachments=[],
            html='',
            inlines=[],
            message_id=None,
            original_cc_address=[],
            original_to_address=['canvas-123-456@example.edu'],
            text='blah blah'
        )
        ml.send_mail.assert_has_calls([send_mail_call])

    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_email_to_multiple_sections_when_always_mail_staff_false(self, mock_ml_get, mock_ci_get, mock_ss_filter):
        """
        TLT-2960

        When the always_mail_staff course setting is False, and multiple
        sections are simultaneously emailed, the sender gets multiple emails
        """
        # prep a MailingList mock, teacher not in section
        members = [{'address': a} for a in ['unittest@example.edu', 'student@example.edu']]

        cs = MagicMock(always_mail_staff=False)

        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher1@example.edu', 'teacher2@example.edu'},
            members=members,
            address='class-list@example.edu',
            course_settings=cs
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value = []

        # prep the post body

        # send mail to multiple  canvas sections
        recipients = ', '.join(['canvas-123-456@example.edu', 'canvas-789-456@example.edu'])
        post_body = {
            'sender': 'Unit Test <teacher1@example.edu>',
            'recipient': recipients,
            'subject': 'blah',
            'body-plain': 'blah blah',
            'To': recipients
        }
        post_body.update(generate_signature_dict())
        print((" post_body=", post_body))

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)
        send_mail_call = call(
            'Unit Test via Canvas',
            'teacher1@example.edu',
            ['teacher1@example.edu', 'student@example.edu','unittest@example.edu'],
            '[Lorem For Beginners] blah',
            attachments=[],
            html='',
            inlines=[],
            message_id=None,
            original_cc_address=[],
            original_to_address=['canvas-123-456@example.edu','canvas-789-456@example.edu'],
            text='blah blah'
        )
        ml.send_mail.assert_has_calls([send_mail_call, send_mail_call])
        self.assertEqual(ml.send_mail.call_count, 2)

    @patch('mailgun.route_handlers._send_bounce')
    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_bounce_loop_detection(self, mock_ml_get, mock_ci_get, mock_ss_filter, mock_send_bounce):
        '''
        TLT-2114
        Verifies that we're dropping emails when they seem to be in a bounce loop.
        '''
        list_address = 'list.address@example.edu'

        # prep the post body
        post_body = {
            'sender': 'Unit Test <unittest@example.edu>',
            'from': settings.NO_REPLY_ADDRESS,
            'recipient': list_address,
            'subject': 'blah',
            'body-plain': 'blah blah',
            'To': list_address,
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)

        # verify we didn't send any mail
        self.assertEqual(mock_ml_get.return_value.send_mail.call_count, 0)
        self.assertEqual(mock_send_bounce.call_count, 0)

    @patch('mailgun.route_handlers.get_name_for_email')
    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_sender_display_name_from_field(self, mock_ml_get, mock_ci_get, mock_ss_filter,
                                            mock_get_name_for_email):
        '''
        TLT-2160
        Verifies that if the mailgun `sender` field lacks a display name, we'll
        use the one in the mailfun `from` field before resorting to enrollee
        lookup.
        '''
        list_address = 'class-list@example.edu'

        # prep a MailingList mock
        members = [{'address': a} for a in [self.user.email, 'student@example.edu']]
        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher@example.edu'},
            members=members,
            address=list_address
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value = []

        # prep the post body
        post_body = {
            'To': list_address,
            'body-plain': 'blah blah',
            'from': '{} <{}>'.format(self.user.get_full_name(), self.user.email),
            'recipient': list_address,
            'sender': self.user.email,
            'subject': 'display name test',
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)

        # verify we didn't fall back to get_name_for_email()
        self.assertEqual(mock_get_name_for_email.call_count, 0)

        # verify we sent mail with the correct sender display name
        self.assertEqual(ml.send_mail.call_count, 1)
        self.assertEqual(ml.send_mail.call_args[0][0],
                         self.user.get_full_name() + ' via Canvas')

    @patch('mailgun.route_handlers.get_name_for_email')
    @patch('mailgun.route_handlers.SuperSender.objects.filter')
    @patch('mailgun.route_handlers.CourseInstance.objects.get_primary_course_by_canvas_course_id')
    @patch('mailgun.route_handlers.MailingList.objects.get_or_create_or_delete_mailing_list_by_address')
    def test_sender_display_name_from_enrollment(self, mock_ml_get, mock_ci_get,
                                                 mock_ss_filter, mock_get_name_for_email):
        '''
        TLT-2160
        Verifies that if the mailgun `sender` and `from` fields lack display
        names, we fall back to enrollee lookup.
        '''
        list_address = 'class-list@example.edu'

        # prep a MailingList mock
        members = [{'address': a} for a in [self.user.email, 'student@example.edu']]
        ml = MagicMock(
            canvas_course_id=123,
            section_id=456,
            teaching_staff_addresses={'teacher@example.edu'},
            members=members,
            address=list_address
        )
        mock_ml_get.return_value = ml

        # prep a CourseInstance mock
        ci = MagicMock(course_instance_id=789,
                       canvas_course_id=ml.canvas_course_id,
                       short_title='Lorem For Beginners',
                       course=MagicMock(school_id='colgsas'))
        mock_ci_get.return_value = ci

        # prep the SuperSender result
        mock_ss_filter.return_value.values_list.return_value=[]

        # prep the mock_get_name_for_email result
        mock_get_name_for_email.return_value = self.user.get_full_name()

        # prep the post body
        post_body = {
            'To': list_address,
            'body-plain': 'blah blah',
            'from': self.user.email,
            'recipient': list_address,
            'sender': self.user.email,
            'subject': 'display name test',
        }
        post_body.update(generate_signature_dict())

        # prep the request
        request = self.factory.post('/', post_body)
        request.user = self.user

        # run the view, verify success
        response = handle_mailing_list_email_route(request)
        self.assertEqual(response.status_code, 200)

        # verify we made the correct call to get_name_for_email()
        self.assertEqual(mock_get_name_for_email.call_count, 1)
        self.assertEqual(mock_get_name_for_email.call_args,
                         call(ml.canvas_course_id, self.user.email))

        # verify we tried to send email with the correct sender display name
        self.assertEqual(ml.send_mail.call_count, 1)
        self.assertEqual(ml.send_mail.call_args[0][0],
                         self.user.get_full_name() + ' via Canvas')


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
        key=settings.LISTSERV_API_KEY.encode('utf-8'),
        msg='{}{}'.format(timestamp, token).encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return {
        'timestamp': timestamp,
        'token': token,
        'signature': signature
    }
