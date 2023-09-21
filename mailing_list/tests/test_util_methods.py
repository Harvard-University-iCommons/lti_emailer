from django.test import TestCase

from mock import patch

from mailing_list.utils import get_section_sis_enrollment_status, is_course_crosslisted
from coursemanager.models import CourseInstance, XlistMap


class CourseInstanceStub:
    """ CourseInstance stub """
    def __init__(self, cs_class_type):
        self.cs_class_type = cs_class_type


class MailingListUtilsTests(TestCase):
    """ tests for the methods in utils.py """
    longMessage = True

    def setUp(self):
        self.course_instance_id = 333444
        self.section = {
            'sis_section_id': '234567',
        }

    @patch('mailing_list.utils.CourseInstance.objects.get')
    def test_get_section_sis_enrollment_status_for_course_with_no_courseinstance(self, mock_get_ci):
        """ Test that the method returns None when there is no record for the section """
        mock_get_ci.side_effect = CourseInstance.DoesNotExist
        result = get_section_sis_enrollment_status(self.section['sis_section_id'])
        self.assertEqual(result, None)

    @patch('mailing_list.utils.CourseInstance.objects.get')
    def test_get_section_sis_enrollment_status_when_cs_class_type_is_none(self, mock_get_ci):
        """ Test that the method returns 'E' when there is a record but the cs_class_type field in empty """
        mock_get_ci.return_value = CourseInstanceStub(None)
        result = get_section_sis_enrollment_status(self.section['sis_section_id'])
        self.assertEqual(result, 'E')

    @patch('mailing_list.utils.CourseInstance.objects.get')
    def test_get_section_sis_enrollment_status_when_cs_class_type_is_E(self, mock_get_ci):
        """ Test that the method returns 'E' when the cs_class_type field is 'E' """
        mock_get_ci.return_value = CourseInstanceStub('E')
        result = get_section_sis_enrollment_status(self.section['sis_section_id'])
        self.assertEqual(result, 'E')

    @patch('mailing_list.utils.CourseInstance.objects.get')
    def test_get_section_sis_enrollment_status_when_cs_class_type_is_N(self, mock_get_ci):
        """ Test that the method returns 'N' when the cs_class_type field is 'N' """
        mock_get_ci.return_value = CourseInstanceStub('N')
        result = get_section_sis_enrollment_status(self.section['sis_section_id'])
        self.assertEqual(result, 'N')

    @patch('mailing_list.utils.CourseInstance.objects.get')
    def test_get_section_sis_enrollment_status_when_cs_class_type_is_G(self, mock_get_ci):
        """ Test that the method returns 'N' when the cs_class_type field is any other value """
        mock_get_ci.return_value = CourseInstanceStub('G')
        result = get_section_sis_enrollment_status(self.section['sis_section_id'])
        self.assertEqual(result, 'N')

    @patch('mailing_list.utils.XlistMap.objects.filter')
    def test_is_course_crosslisted_when_there_is_no_xlist_record(self, mock_get_xref):
        """ Test that the method returns False when there is not a xlist record """
        mock_get_xref.return_value.count.return_value = 0
        result = is_course_crosslisted(self.course_instance_id)
        self.assertEqual(result, False)

    @patch('mailing_list.utils.XlistMap.objects.filter')
    def test_is_course_crosslisted_when_there_is_a_xlist_record(self, mock_get_xref):
        """ Test that the method returns True when there is a record is the xlist table """
        mock_get_xref.return_value.count.return_value = 2
        result = is_course_crosslisted(self.course_instance_id)
        self.assertEqual(result, True)
