from django.conf import settings
from django.test import TestCase

from mock import patch

from mailing_list.models import MailingList


class MailingListModelTests(TestCase):
    fixtures = [
        'mailing_list/fixtures/test_mailing_list.json'
    ]
    longMessage = True

    def setUp(self):
        self.sections = [{
            'id': 1582,
            'name': 'section name 1',
            'sis_section_id': '334562',
        }, {
            'id': 1583,
            'name': 'section name 2',
            'sis_section_id': None,
        }]

    @patch('mailing_list.models.get_section_sis_enrollment_status')
    @patch('mailing_list.models.is_course_crosslisted')
    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_existing_list(self, mock_get_sections,
                                                                                           mock_get_enrollments,
                                                                                           mock_get_course,
                                                                                           mock_xlisted,
                                                                                           mock_get_sis_enroll_stat):
        mock_get_course.return_value = {'sis_course_id': '786534'}
        mock_xlisted.return_value = False
        mock_get_sis_enroll_stat.return_value = None

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
        address_0 = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716
        )

        self.assertEqual(result, [{
             'access_level': u'members',
            'members_count': 0,
            'name': 'Course Mailing List',
            'cs_class_type': None,
            'sis_section_id': None,
            'address': address_0,
            'canvas_course_id': 3716,
            'id': 3,
            'is_course_list': True,
            'is_primary': False,
            'section_id': None
            },{
            'access_level': u'members',
            'members_count': 0,
            'name': 'section name 1',
            'cs_class_type': None,
            'sis_section_id': '334562',
            'address': address_1,
            'canvas_course_id': 3716,
            'id': 1,
            'is_course_list': False,
            'is_primary': False,
            'section_id': 1582
        },{
            'access_level': u'members',
            'members_count': 0,
            'name': 'section name 2',
            'cs_class_type': None,
            'sis_section_id': None,
            'address': address_2,
            'canvas_course_id': 3716,
            'id': 2,
            'is_primary': False,
            'is_course_list': False,
            'section_id': 1583
        }])


    @patch('mailing_list.models.get_section_sis_enrollment_status')
    @patch('mailing_list.models.is_course_crosslisted')
    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_new_list(self, mock_get_sections,
                                                                                      mock_get_enrollments,
                                                                                      mock_get_course,
                                                                                      mock_xlisted,
                                                                                      mock_get_sis_enroll_stat):

        mock_get_course.return_value = {'sis_course_id': '786534'}
        mock_xlisted.return_value = False
        mock_get_sis_enroll_stat.return_value = 'E'

        sections = list(self.sections)
        sections.append({
            'id': 1584,
            'name': 'section name 3',
            'sis_section_id': None
        })
        mock_get_sections.return_value = sections
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        address_0 = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716
        )
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
                'access_level': u'members',
                'members_count': 0,
                'name': 'Course Mailing List',
                'cs_class_type': None,
                'sis_section_id': None,
                'address': address_0,
                'canvas_course_id': 3716,
                'id': 3,
                'is_course_list': True,
                'is_primary': False,
                'section_id': None
            },{
                'access_level': u'members',
                'members_count': 0,
                'name': 'section name 1',
                'cs_class_type': 'E',
                'sis_section_id': '334562',
                'address': address_1,
                'canvas_course_id': 3716,
                'id': 1,
                'is_course_list': False,
                'is_primary': False,
                'section_id': 1582
            },{
                'access_level': u'members',
                'members_count': 0,
                'name': 'section name 2',
                'cs_class_type': None,
                'sis_section_id': None,
                'address': address_2,
                'canvas_course_id': 3716,
                'id': 2,
                'is_course_list': False,
                'is_primary': False,
                'section_id': 1583
            },{
                'access_level': 'members',
                'members_count': 0,
                'name': 'section name 3',
                'cs_class_type': None,
                'sis_section_id': None,
                'address': address_3,
                'canvas_course_id': 3716,
                'id': 4,
                'is_course_list': False,
                'is_primary': False,
                'section_id': 1584
            }], result)

    @patch('mailing_list.models.get_section_sis_enrollment_status')
    @patch('mailing_list.models.is_course_crosslisted')
    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_deleted_section(self, mock_get_sections,
                                                                                             mock_get_enrollments,
                                                                                             mock_get_course,
                                                                                             mock_xlisted,
                                                                                             mock_get_sis_enroll_stat):
        mock_get_course.return_value = {'sis_course_id': '786534'}
        mock_xlisted.return_value = False
        mock_get_sis_enroll_stat.return_value = None
        sections = list(self.sections)
        del sections[1]
        mock_get_sections.return_value = sections
        mock_get_enrollments.return_value = []

        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        address_0 = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716
        )
        address_1 = settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
            section_id=1582
        )

        self.assertEqual([{
            'access_level': u'members',
            'members_count': 0,
            'name': 'Course Mailing List',
            'cs_class_type': None,
            'sis_section_id': None,
            'address': address_0,
            'canvas_course_id': 3716,
            'id': 3,
            'is_course_list': True,
            'is_primary': False,
            'section_id': None
            },{
            'access_level': u'members',
            'members_count': 0,
            'name': 'section name 1',
            'cs_class_type': None,
            'sis_section_id': '334562',
            'address': address_1,
            'canvas_course_id': 3716,
            'id': 1,
            'is_course_list': False,
            'is_primary': False,
            'section_id': 1582}], result)

    @patch('mailing_list.models.get_section_sis_enrollment_status')
    @patch('mailing_list.models.is_course_crosslisted')
    @patch('mailing_list.models.MailingList.objects.get')
    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_multiple_primary_sections(self,
                                                                                                       mock_get_sections,
                                                                                                       mock_get_enrollments,
                                                                                                       mock_get_course,
                                                                                                       mock_get_mailinglist,
                                                                                                       mock_xlisted,
                                                                                                       mock_get_sis_enroll_stat):
        """
        Test that a new mailing list is created when the course has multiple primary sections. The address of this new list
        should contain only the course id and the newly created list should have a section id of 'None'.
        """
        mock_xlisted.return_value = True
        mock_get_sis_enroll_stat.return_value = 'E'
        mock_get_mailinglist.side_effect = MailingList.DoesNotExist

        sections = list(self.sections)
        mock_get_course.return_value = {
            'course_code' : 'Test Course',
            'sis_course_id': '786534',
        }

        mock_get_sections.return_value = sections

        # append a second primary section
        sections.append({
            'id': None,
            'name': 'Test Course',
            'sis_section_id': '123456'
        })

        mock_get_enrollments.return_value = []
        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)

        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
        )

        self.assertEqual({
            'access_level': 'members',
            'members_count': 0,
            'name': 'Course Mailing List',
            'cs_class_type': None,
            'sis_section_id': None,
            'address': list_address,
            'canvas_course_id': 3716,
            'id': 3,
            'is_course_list': True,
            'is_primary': False,
            'section_id': None
        }, result[0])

    @patch('mailing_list.models.get_section_sis_enrollment_status')
    @patch('mailing_list.models.is_course_crosslisted')
    @patch('mailing_list.models.MailingList.objects.get')
    @patch('mailing_list.models.canvas_api_client.get_course')
    @patch('mailing_list.models.canvas_api_client.get_enrollments')
    @patch('mailing_list.models.canvas_api_client.get_sections')
    def test_get_or_create_or_delete_mailing_lists_for_canvas_course_id_with_non_crosslisted_course(self,
                                                                                                       mock_get_sections,
                                                                                                       mock_get_enrollments,
                                                                                                       mock_get_course,
                                                                                                       mock_get_mailinglist,
                                                                                                       mock_xlisted,
                                                                                                       mock_get_sis_enroll_stat):
        """
        Test that a  meta  mailing list is created even for a regular, non cross listed course. The address of this new
        list should contain only the course id and the newly created list should have a section id of 'None'.
        """
        mock_xlisted.return_value = False
        mock_get_sis_enroll_stat.return_value = 'E'
        mock_get_mailinglist.side_effect = MailingList.DoesNotExist

        sections = list(self.sections)
        mock_get_course.return_value = {
            'course_code': 'Test Course',
            'sis_course_id': '334562',
        }

        mock_get_sections.return_value = sections

        mock_get_enrollments.return_value = []
        result = MailingList.objects.get_or_create_or_delete_mailing_lists_for_canvas_course_id(3716)
        # address of the course list should be set in new mailing list
        list_address = settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(
            canvas_course_id=3716,
        )

        self.assertEqual({
            'access_level': 'members',
            'members_count': 0,
            'name': 'Course Mailing List',
            'cs_class_type': None,
            'sis_section_id': None,
            'address': list_address,
            'canvas_course_id': 3716,
            'id': 3,
            'is_course_list': True,
            'is_primary': False,
            'section_id': None
        }, result[0])
        # Assert that a course with 2 sections has a total of 3 mailing lists incuding the meta mailing list
        self.assertEqual(3, len(result))

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
            'sis_section_id': '123456',
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


