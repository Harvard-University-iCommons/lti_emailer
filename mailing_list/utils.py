import logging

from icommons_common.models import XlistMap

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

    return course_is_crosslisted

