from django.conf import settings
from django.test import TestCase

from mock import patch

from .models import MailingList


class MailingListModelTests(TestCase):
    fixtures = [
        'mailing_list/fixtures/test_mailing_list.json'
    ]
    longMessage = True

    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_existing_list(self, mock_get_sections,
                                                                                 mock_get_enrollments):
        mock_get_sections.return_value = [{
            'id': 1582,
            'name': 'section name',
            'sis_section_id': 334562
        }]
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(3716)
        address = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )

        self.assertEqual(result, [{
            'id': 1,
            'canvas_course_id': 3716,
            'section_id': 1582,
            'name': 'section name',
            'address': address,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }])

    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_mailing_lists_for_canvas_course_id_with_new_list(self, mock_get_sections,
                                                                            mock_get_enrollments):
        mock_get_sections.return_value = [{
            'id': 1583,
            'name': 'section name 1',
            'sis_section_id': 334562
        }, {
            'id': 1584,
            'name': 'section name 2',
            'sis_section_id': None
        }]
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_mailing_lists_for_canvas_course_id(3716)
        address_1 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1583
        )
        address_2 = settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1584
        )

        self.assertIn({
            'id': 2,
            'canvas_course_id': 3716,
            'section_id': 1583,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }, result)
        self.assertIn({
            'id': 3,
            'canvas_course_id': 3716,
            'section_id': 1584,
            'name': 'section name 2',
            'address': address_2,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': False
        }, result)
