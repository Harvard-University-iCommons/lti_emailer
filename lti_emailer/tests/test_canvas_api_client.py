from __future__ import unicode_literals

from django.test import TestCase
from mock import patch

from lti_emailer.canvas_api_client import get_alternate_emails_for_user_email


@patch('lti_emailer.canvas_api_client.get_users_in_course')
@patch('lti_emailer.canvas_api_client._list_user_comm_channels')
class GetAlternateEmailsForUserEmailTests(TestCase):
    longMessage = True

    def test_no_users(self, mock_comm_channels, mock_users):
        test_address = 'a@b.c'
        mock_users.return_value = [{'id': 1, 'email': 'b@o.gus'}]

        emails = get_alternate_emails_for_user_email(1, test_address)

        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 0)
        self.assertEqual(mock_comm_channels.call_count, 0)

    def test_multiple_user_matches(self, mock_comm_channels, mock_users):
        test_address = 'a@b.c'
        first_user_id = 1
        second_user_id = 2
        self.assertNotEqual(first_user_id, second_user_id)  # sanity check

        mock_users.return_value = [
            {'id': first_user_id, 'email': 'a@b.c'},
            {'id': second_user_id, 'email': 'a@b.c'}]
        mock_comm_channels.return_value = []

        emails = get_alternate_emails_for_user_email(1, test_address)

        self.assertTrue(mock_comm_channels.called_once_with(first_user_id))
        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 0)

    def test_valid_channel_filter(self, mock_comm_channels, mock_users):
        test_address = 'a@b.c'
        valid_address = 'd@e.f'
        invalid_address = 'g@h.i'
        self.assertNotEqual(valid_address, invalid_address)  # sanity check

        mock_users.return_value = [{'id': 1, 'email': 'a@b.c'}]
        mock_comm_channels.return_value = [
            {'address': valid_address, 'type': 'email', 'workflow_state': 'active'},
            {'address': invalid_address, 'type': 'sms', 'workflow_state': 'active'},
            {'address': invalid_address, 'workflow_state': 'active'},
            {'address': invalid_address, 'type': 'email', 'workflow_state': 'unconfirmed'},
            {'address': invalid_address, 'type': 'email'},
            {'type': 'email', 'workflow_state': 'active'}]

        emails = get_alternate_emails_for_user_email(1, test_address)

        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0], valid_address)
