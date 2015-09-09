from django.conf import settings
from django.test import TestCase

from mock import patch, call

from .models import MailingList


class MailingListModelTests(TestCase):
    fixtures = [
        'mailing_list/fixtures/test_mailing_list.json'
    ]
    longMessage = True

    def setUp(self):
        self.sections = [{
            'id': 1582,
            'name': 'section name 1',
            'sis_section_id': 334562
        }, {
            'id': 1583,
            'name': 'section name 2',
            'sis_section_id': None
        }]

    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_existing_list(self, mock_get_sections,
                                                                                           mock_get_enrollments):
        mock_get_sections.return_value = self.sections
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        address_1 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )
        address_2 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1583
        )

        self.assertEqual(result, [{
            'id': 1,
            'canvas_course_id': 3716,
            'section_id': 1582,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }, {
            'id': 2,
            'canvas_course_id': 3716,
            'section_id': 1583,
            'name': 'section name 2',
            'address': address_2,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': False
        }])

    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_new_list(self, mock_get_sections,
                                                                                      mock_get_enrollments):
        sections = list(self.sections)
        sections.append({
            'id': 1584,
            'name': 'section name 3',
            'sis_section_id': None
        })
        mock_get_sections.return_value = sections
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        address_1 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )
        address_2 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1583
        )
        address_3 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1584
        )

        self.assertEqual([{
            'id': 1,
            'canvas_course_id': 3716,
            'section_id': 1582,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }, {
            'id': 2,
            'canvas_course_id': 3716,
            'section_id': 1583,
            'name': 'section name 2',
            'address': address_2,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': False
        }, {
            'id': 3,
            'canvas_course_id': 3716,
            'section_id': 1584,
            'name': 'section name 3',
            'address': address_3,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': False
        }], result)

    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_deleted_section(self, mock_get_sections,
                                                                                             mock_get_enrollments):
        sections = list(self.sections)
        del sections[1]
        mock_get_sections.return_value = sections
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        address_1 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )

        self.assertEqual([{
            'id': 1,
            'canvas_course_id': 3716,
            'section_id': 1582,
            'name': 'section name 1',
            'address': address_1,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }], result)

    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_multiple_primary_sections(self,
                                                                                                       mock_get_sections,
                                                                                                       mock_get_enrollments,
                                                                                                       mock_get_course):
        """
        Test that a new mailing list is created when the course has multiple primary sections. The address of this new list
        should contain only the course id and the newly created list should have a section id of 'None'.
        """
        sections = list(self.sections)
        mock_get_course.return_value = {
            'course_code' : 'Test Course',
        }

        mock_get_sections.return_value = sections

        # append a second primary section
        sections.append({
            'id': None,
            'name': 'Test Course',
            'sis_section_id': 123456
        })

        mock_get_enrollments.return_value = []
        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)

        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
        )

        self.assertEqual({
            'id': 4,
            'canvas_course_id': 3716,
            'section_id': None,
            'name': 'Test Course',
            'address': list_address,
            'access_level': 'members',
            'members_count': 0,
            'is_primary_section': True
        }, result[-1])

    def test_parse_address_with_course_list(self):
        """ test that _parse_address return the correct data for the course list address """
        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
        )
        result = MailingList.objects._parse_address(list_address)
        self.assertEqual((3716, None), result)

    def test_parse_address_with_section_list(self):
        """ test that _parse_address return the correct data for a section list address """
        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=12345
        )
        result = MailingList.objects._parse_address(list_address)
        self.assertEqual((3716, 12345), result)

    def test_parse_address_throws_doesnotexist_when_no_match_is_found(self):
        """ test that _parse_address raises a DoesNotExist exception when an invalid address is passed in """
        # address of the course list should be set in new mailing list
        list_address = "somename12345@mydomain.com"
        with self.assertRaises(MailingList.DoesNotExist):
            MailingList.objects._parse_address(list_address)

    @patch('mailing_list.models.canvas_api_client.get_section')
    @patch('mailing_list.models.MailingList.objects.get')
    def test_get_or_create_or_delete_mailing_list_by_address_with_section_calls_get_with_correct_args(self,
                                                                                                      mock_get_mailing_list,
                                                                                                      mock_get_section):
        """ test that get_or_create_or_delete_mailing_list_by_address with section calls get with
        correct args """
        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=12345
        )

        mock_get_section.return_value = {
            'id': 12345,
            'name': 'test',
            'sis_section_id': 123456,
        }

        MailingList.objects.get_or_create_or_delete_mailing_list_by_address(list_address)
        mock_get_mailing_list.assert_called_with(canvas_course_id=3716, section_id=12345)


    @patch('mailing_list.models.canvas_api_client.get_section')
    @patch('mailing_list.models.MailingList.objects.get')
    def test_get_or_create_or_delete_mailing_list_by_address_with_none_as_section_calls_get_with_correct_args(self,
                                                                                                              mock_get_mailing_list,
                                                                                                              mock_get_section):
        """ test that get_or_create_or_delete_mailing_list_by_address with None as section calls get with
        correct args """
        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
        )

        mock_get_section.return_value = None
        MailingList.objects.get_or_create_or_delete_mailing_list_by_address(list_address)
        mock_get_mailing_list.assert_called_with(canvas_course_id=3716, section_id__isnull=True)

