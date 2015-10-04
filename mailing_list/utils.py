import logging

from icommons_common.models import CourseInstance, XlistMap

logger = logging.getLogger(__name__)


def is_course_crosslisted(course_instance_id):
    """
    Check the XListMap table to see if the course is crosslisted
    :param course_instance_id:
    :return Bool:
    """
    try:
        xlistentry = XlistMap.objects.get(primary_course_instance=course_instance_id)
        course_is_crosslisted = True
    except XlistMap.DoesNotExist:
        course_is_crosslisted = False

    return True
    #return course_is_crosslisted


def get_section_sis_enrollment_status(sis_section_id):
    """
    Check to see if the section was fed by the SIS. If it was, it will have a field set
    called cs_class_type with a value of either 'N' (non enrollment) or 'E' (enrollment).
    If the value is 'N' the section was created by an end user in Campus solutions. We want
    to be able to differentiate which sections were created by users from ones that were not.

    SIS fed sections have an sis_section_id that corresponds to a course_instance_id in the
    CourseInstance model.

    :param sis_section_id:
    :return 'N', 'E', or None:
    """
    try:
        ci = CourseInstance.objects.get(course_instance_id=int(sis_section_id))
        # if there is a course instance but there is no cs_class_type
        # we should assume this is an enrollment type so return 'E'
        if not ci.cs_class_type or ci.cs_class_type in 'E':
            return 'E'
        else:
            # the only other option is 'N' so just return it
            return 'N'

    except CourseInstance.DoesNotExist:
        # there was no record for this id, so return None
        return None
