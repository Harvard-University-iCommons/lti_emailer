import uuid

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from mock import MagicMock, patch

from .models import MailingList
from .tasks import course_sync_listserv


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
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_existing_list(
            self, mock_get_sections, mock_get_list, mock_create_list, mock_sync_listserv_membership):
        mock_get_sections.return_value = [{
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
            'canvas_course_id': 3716,
            'section_id': 1582,
            'name': 'section name',
            'address': address,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': True
        }])

    @patch('mailing_list.models.MailingList.sync_listserv_membership')
    @patch('mailing_list.models.listserv_client.create_list')
    @patch('mailing_list.models.listserv_client.get_list')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_new_list(
            self, mock_get_sections, mock_get_list, mock_create_list, mock_sync_listserv_membership):
        mock_get_sections.return_value = [{
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

        result = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(3716)
        address_1 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1583
        )
        address_2 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1584
        )

        self.assertTrue(mock_create_list.called, 'ListservClient.create_list not called and it should have been')
        self.assertIn({
            'id': 2,
            'canvas_course_id': 3716,
            'section_id': 1583,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': True
        }, result)
        self.assertIn({
            'id': 3,
            'canvas_course_id': 3716,
            'section_id': 1584,
            'name': 'section name 2',
            'address': address_2,
            'access_level': 'members',
            'members_count': 1,
            'is_primary_section': False
        }, result)


class TaskQueueTests(TestCase):
    """
    Huey's django integration doesn't play nicely with unit tests.  In
    particular, the decorators it provides instantiate a module-global
    Huey object at module load time.  That means that override_settings
    is useless in this case.  We could edit the huey.djhuey.HUEY object
    directly, but really, then we're just testing huey itself.

    Thus, the tests here focus just on the functionality being invoked
    by the huey tasks.
    """
    longMessage = True

    @patch('mailing_list.tasks.MailingList.objects.filter')
    def test_sync_no_args(self, mock_objects_filter):
        course_id = uuid.uuid4().hex
        mock_mailing_list = MagicMock(canvas_course_id=course_id)
        mock_objects_filter.return_value = [mock_mailing_list]

        course_sync_listserv(None)

        mock_objects_filter.assert_called_once_with()
        mock_mailing_list.sync_listserv_membership.assert_called_once_with()

    @patch('mailing_list.tasks.MailingList.objects.filter')
    def test_sync_one_course_id(self, mock_objects_filter):
        course_id = uuid.uuid4().hex
        mock_mailing_list = MagicMock(canvas_course_id=course_id)
        mock_objects_filter.return_value = [mock_mailing_list]

        course_sync_listserv(course_id)

        mock_objects_filter.assert_called_once_with(canvas_course_id__in=[course_id])
        mock_mailing_list.sync_listserv_membership.assert_called_once_with()

    @patch('mailing_list.tasks.MailingList.objects.filter')
    def test_sync_many_course_ids(self, mock_objects_filter):
        mock_mailing_lists = [MagicMock(canvas_course_id=uuid.uuid4().hex) for _ in xrange(5)]
        course_ids = [ml.canvase_course_id for ml in mock_mailing_lists]
        mock_objects_filter.return_value = mock_mailing_lists

        course_sync_listserv(course_ids)

        mock_objects_filter.assert_called_once_with(canvas_course_id__in=course_ids)
        for mock_ml in mock_mailing_lists:
            mock_ml.sync_listserv_membership.assert_called_once_with()
