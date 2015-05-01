"""
Utility methods for working with canvas_python_sdk which add a caching layer to the Canvas API calls.

TODO: Incorporate this caching layer into canvas_python_sdk. Punting on this for now to limit collateral concerns.
"""
import logging
import json

from django.conf import settings
from django.core.cache import cache

from canvas_sdk.methods import enrollments, sections
from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.canvas_utils import SessionInactivityExpirationRC


logger = logging.getLogger(__name__)

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


def get_sections(canvas_course_id):
    cache_key = settings.CACHE_KEY_CANVAS_SECTIONS_BY_CANVAS_COURSE_ID % canvas_course_id
    result = cache.get(cache_key)
    if not result:
        try:
            result = get_all_list_data(SDK_CONTEXT, sections.list_course_sections, canvas_course_id)
        except CanvasAPIError:
            logger.exception("Failed to get canvas sections for canvas_course_id %s", canvas_course_id)
            raise

        cache.set(cache_key, result)

    return result


def get_enrollments(canvas_course_id, section_id):
    cache_key = settings.CACHE_KEY_CANVAS_ENROLLMENTS_BY_CANVAS_SECTION_ID % section_id
    result = cache.get(cache_key)
    if not result:
        try:
            result = get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_sections, section_id)
            print json.dumps(result, indent=4)
        except CanvasAPIError:
            logger.exception(
                "Failed to get canvas enrollments for canvas_course_id %s and section_id %s",
                canvas_course_id,
                section_id
            )
            raise

        cache.set(cache_key, result)

    return result
