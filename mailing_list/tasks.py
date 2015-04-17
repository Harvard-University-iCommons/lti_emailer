"""
Defines huey tasks to sync mailing list membership from our systems out to
the listserv service.
"""

import collections
import logging

from django.conf import settings
from huey.djhuey import crontab, db_task, db_periodic_task

from canvas_sdk.exceptions import CanvasAPIError

from mailing_list.models import MailingList
from mailing_list.listserv_clients.exceptions import ListservApiError


logger = logging.getLogger(__name__)

# if we don't supply a default, huey will run it every minute.  let's opt
# for once an hour instead.
DEFAULT_LISTSERV_PERIODIC_SYNC_CRONTAB = {'minute': '0'}


@db_task()
def sync_listserv(course_ids=None):
    course_sync_listserv(course_ids)


@db_periodic_task(
    crontab(**getattr(settings, 'LISTSERV_PERIODIC_SYNC_CRONTAB',
                                DEFAULT_LISTSERV_PERIODIC_SYNC_CRONTAB)))
def periodic_sync_listserv():
    course_sync_listserv(None)


def course_sync_listserv(course_ids):
    filter_kwargs = {}
    if course_ids:
        if (not isinstance(course_ids, collections.Iterable)
                or isinstance(course_ids, basestring)):
            course_ids = [course_ids]
        filter_kwargs['canvas_course_id__in'] = course_ids

    success_course_ids, failure_course_ids = [], []
    for mailing_list in MailingList.objects.filter(**filter_kwargs):
        try:
            mailing_list.sync_listserv_membership()
        except (CanvasAPIError, ListservApiError):
            failure_course_ids.append(mailing_list.canvas_course_id)
            logger.exception('Unable to sync canvas course id {}'.format(
                                 mailing_list.canvas_course_id))
        else:
            success_course_ids.append(mailing_list.canvas_course_id)

    logger.info('Finished syncing listserv memberships.  Course ids {} '
                'succeeded, course ids {} failed'.format(
                    success_course_ids, failure_course_ids))
