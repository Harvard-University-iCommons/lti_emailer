import logging

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from mailing_list.models import MailingList


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronizes mailing lists created for canvas courses with the enrollment list for each course'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        logger.info("Beginning sync_listserv job for canvas_course_ids %s", args)
        try:
            canvas_course_ids = []
            if args:
                for ml in MailingList.objects.filter(canvas_course_id__in=args):
                    canvas_course_ids.append(ml.canvas_course_id)
                    ml.sync_listserv_membership()
            else:
                for ml in MailingList.objects.all():
                    canvas_course_ids.append(ml.canvas_course_id)
                    ml.sync_listserv_membership()

            for canvas_course_id in canvas_course_ids:
                cache.delete(settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % canvas_course_id)

            logger.info("Finished sync_listserv job for canvas_course_ids %s", canvas_course_ids)
        except Exception:
            message = "Error encountered while synchronizing mailing lists for canvas course ids %s" % canvas_course_ids
            logger.exception(message)
            raise CommandError(message)
