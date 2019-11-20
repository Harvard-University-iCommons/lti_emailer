

from django.test import TestCase
from mock import patch

from lti_emailer.canvas_api_client import get_alternate_emails_for_user_email


@patch('lti_emailer.canvas_api_client._get_users_by_email')
@patch('lti_emailer.canvas_api_client._list_user_comm_channels')
class GetAlternateEmailsForUserEmailTests(TestCase):
    longMessage = True

    def test_no_users(self, mock_comm_channels, mock_users):
        test_address = 'a@b.c'
        mock_users.return_value = []

        emails = get_alternate_emails_for_user_email(test_address)

        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 0)
        self.assertEqual(mock_comm_channels.call_count, 0)

    def test_multiple_user_matches(self, mock_comm_channels, mock_users):
        """
        should return de-duped set of email addresses for all matching users
        """
        test_address_a = 'a@b.c'
        test_address_b = 'b@c.d'
        first_user_id = 1
        second_user_id = 2
        first_user_cc_list = [
            {'address': test_address_a, 'type': 'email', 'workflow_state': 'active'}]
        second_user_cc_list = [
            {'address': test_address_a, 'type': 'email', 'workflow_state': 'active'},
            {'address': test_address_b, 'type': 'email', 'workflow_state': 'active'}]

        self.assertNotEqual(first_user_id, second_user_id)  # sanity check

        mock_users.return_value = [
            {'id': first_user_id, 'email': test_address_a},
            {'id': second_user_id, 'email': test_address_a}]
        mock_comm_channels.side_effect = [
            first_user_cc_list,
            second_user_cc_list]

        emails = get_alternate_emails_for_user_email(test_address_a)

        self.assertEqual(mock_comm_channels.call_count, 2)
        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 2)
        self.assertIn(test_address_a, emails)
        self.assertIn(test_address_b, emails)

    def test_valid_channel_filter(self, mock_comm_channels, mock_users):
        """
        should only return addresses for active email communication channels
        """
        test_address = 'a@b.c'
        valid_address = 'd@e.f'
        invalid_address = 'g@h.i'
        self.assertNotEqual(valid_address, invalid_address)  # sanity check

        mock_users.return_value = [{'id': 1, 'email': test_address}]
        mock_comm_channels.return_value = [
            {'address': valid_address, 'type': 'email', 'workflow_state': 'active'},
            {'address': invalid_address, 'type': 'sms', 'workflow_state': 'active'},
            {'address': invalid_address, 'workflow_state': 'active'},
            {'address': invalid_address, 'type': 'email', 'workflow_state': 'unconfirmed'},
            {'address': invalid_address, 'type': 'email'},
            {'type': 'email', 'workflow_state': 'active'}]

        emails = get_alternate_emails_for_user_email(test_address)

        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 1)
        self.assertIn(valid_address, emails)

    def test_valid_user_filter(self, mock_comm_channels, mock_users):
        """
        should only look up users whose primary email matches email_address
        argument
        """
        test_address_a = 'a@b.c'
        test_address_b = 'b@c.d'
        first_user_cc_list = [
            {'address': test_address_a, 'type': 'email', 'workflow_state': 'active'}]
        second_user_cc_list = [
            {'address': test_address_b, 'type': 'email', 'workflow_state': 'active'}]

        mock_users.return_value = [
            {'id': 1, 'email': test_address_a},
            {'id': 2, 'email': test_address_b}]
        mock_comm_channels.side_effect = [
            first_user_cc_list,
            second_user_cc_list]

        emails = get_alternate_emails_for_user_email(test_address_a)

        self.assertIsNotNone(emails)
        self.assertEqual(len(emails), 1)
        self.assertIn(test_address_a, emails)
