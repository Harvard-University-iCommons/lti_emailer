from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings

from mock import patch

from .models import MailingList


class MailingListModelTests(TestCase):
    fixtures = [
        'mailing_list/fixtures/test_mailing_list.json',
        'mailing_list/fixtures/test_unsubscribed.json'
    ]
    longMessage = True

    @patch('mailing_list.models.MailingList._get_enrolled_email_set')
    @patch('mailing_list.models.MailingList._get_listserv_email_set')
    @patch('mailing_list.models.listserv_client.add_members')
    @patch('mailing_list.models.listserv_client.delete_members')
    def _call_sync_listserv_membership(self, mock_delete_members, mock_add_members, mock_get_listserv_email_set,
                                       mock_get_enrolled_email_set, **kwargs):
        mock_delete_members.return_value = None
        mock_add_members.return_value = None
        mock_get_listserv_email_set.return_value = kwargs['listserv_email_set']
        mock_get_enrolled_email_set.return_value = kwargs['enrolled_email_set']

        mailing_list = MailingList.objects.get(id=1)
        result = mailing_list.sync_listserv_membership()

        mock_add_members.assert_called_with(mailing_list, kwargs['add_members'])
        mock_delete_members.assert_called_with(mailing_list, kwargs['delete_members'])
        self.assertEqual(result, kwargs['members_count'])

    def test_sync_listserv_membership_add_members_to_listserv(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'sapna_mysore@harvard.edu'
            },
            add_members={'david_bonner@harvard.edu', 'sapna_mysore@harvard.edu'},
            delete_members=set(),
            members_count=4
        )

    def test_sync_listserv_membership_delete_members_from_listserv(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'sapna_mysore@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            add_members=set(),
            delete_members={'david_bonner@harvard.edu', 'sapna_mysore@harvard.edu'},
            members_count=2
        )

    def test_sync_listserv_membership_add_and_delete_members_from_listserv(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'sapna_mysore@harvard.edu'
            },
            add_members={'sapna_mysore@harvard.edu'},
            delete_members={'david_bonner@harvard.edu'},
            members_count=3
        )

    @override_settings(IGNORE_WHITELIST=True)
    def test_sync_listserv_membership_unsubscribed(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'douglas_hall@harvard.edu'
            },
            add_members={'david_bonner@harvard.edu'},
            delete_members=set(),
            members_count=3
        )

    def test_sync_listserv_membership_whitelist_not_set(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'douglashall@g.harvard.edu'
            },
            add_members={'david_bonner@harvard.edu'},
            delete_members=set(),
            members_count=3
        )

    @override_settings(IGNORE_WHITELIST=False)
    def test_sync_listserv_membership_ignore_whitelist_false(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'douglashall@g.harvard.edu'
            },
            add_members={'david_bonner@harvard.edu'},
            delete_members=set(),
            members_count=3
        )

    @override_settings(IGNORE_WHITELIST=True)
    def test_sync_listserv_membership_ignore_whitelist_true(self):
        self._call_sync_listserv_membership(
            listserv_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu'
            },
            enrolled_email_set={
                'hiukei_chow@harvard.edu',
                'david_downs@harvard.edu',
                'david_bonner@harvard.edu',
                'douglashall@g.harvard.edu'
            },
            add_members={'david_bonner@harvard.edu', 'douglashall@g.harvard.edu'},
            delete_members=set(),
            members_count=4
        )

    @patch('mailing_list.models.listserv_client.update_list')
    def test_update_access_level(self, mock_update_list):
        mock_update_list.return_value = None

        mailing_list = MailingList.objects.get(id=1)
        mailing_list.update_access_level('readonly')

        mock_update_list.assert_called_with(mailing_list, 'readonly')

    @patch('mailing_list.models.MailingList.sync_listserv_membership')
    @patch('mailing_list.models.listserv_client.create_list')
    @patch('mailing_list.models.listserv_client.get_list')
    @patch('mailing_list.models.MailingListManager._get_canvas_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_existing_list(
            self, mock_get_canvas_sections, mock_get_list, mock_create_list, mock_sync_listserv_membership):
        mock_get_canvas_sections.return_value = [{
            'id': 1582,
            'name': 'section name',
            'sis_section_id': 334562
        }]
        mock_get_list.return_value = {'access_level': 'members'}
        mock_create_list.return_value = None
        mock_sync_listserv_membership.return_value = 1

        result = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(3716)
        address = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )

        self.assertFalse(mock_create_list.called, 'ListservClient.create_list called and it should not have been')
        self.assertEqual(result, [{
            'id': 1,
            'name': 'section name',
            'address': address,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': True
        }])

    @patch('mailing_list.models.MailingList.sync_listserv_membership')
    @patch('mailing_list.models.listserv_client.create_list')
    @patch('mailing_list.models.listserv_client.get_list')
    @patch('mailing_list.models.MailingListManager._get_canvas_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_new_list(
            self, mock_get_canvas_sections, mock_get_list, mock_create_list, mock_sync_listserv_membership):
        mock_get_canvas_sections.return_value = [{
            'id': 1583,
            'name': 'section name 1',
            'sis_section_id': 334562
        }, {
            'id': 1584,
            'name': 'section name 2',
            'sis_section_id': None
        }]
        mock_get_list.return_value = None
        mock_create_list.return_value = None
        mock_sync_listserv_membership.return_value = 1

        result = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(3718)
        address_1 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3718,
            section_id=1583
        )
        address_2 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3718,
            section_id=1584
        )

        self.assertTrue(mock_create_list.called, 'ListservClient.create_list not called and it should have been')
        self.assertIn({
            'id': 2,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': True
        }, result)
        self.assertIn({
            'id': 3,
            'name': 'section name 2',
            'address': address_2,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': False
        }, result)
