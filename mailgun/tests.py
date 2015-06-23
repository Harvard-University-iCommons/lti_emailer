import json

from django.test import TestCase

from mock import patch

from icommons_common.utils import Bunch

from lti_emailer.exceptions import ListservApiError
from mailing_list.models import MailingList
from .listserv_client import MailgunClient as ListservClient


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
        api_url = "%s/%s" % (listserv_client.api_url, mailing_list.address)
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
        api_url = "%s/%s" % (listserv_client.api_url, mailing_list.address)
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
        api_url = listserv_client.api_url
        auth = (listserv_client.api_user, listserv_client.api_key)
        payload = {
            'address': mailing_list.address,
            'access_level': 'members'
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
        api_url = "%s/%s" % (listserv_client.api_url, mailing_list.address)
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
        api_url = "%s/%s" % (listserv_client.api_url, mailing_list.address)
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
        api_url = "%s/%s/members?limit=100&skip=0" % (listserv_client.api_url, mailing_list.address)
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
        api_url = "%s/%s/members.json" % (listserv_client.api_url, mailing_list.address)
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
        api_url = "%s/%s/members/%s" % (listserv_client.api_url, mailing_list.address, emails[0])
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
