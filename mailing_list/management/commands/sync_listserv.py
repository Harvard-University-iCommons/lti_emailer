import logging

from django.core.management.base import BaseCommand, CommandError

from mailing_list.models import MailingList
from mailing_list.utils import sync_mailing_lists_with_listserv


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronizes mailing lists created for canvas courses with the enrollment list for each course'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        logger.info("Beginning sync_listserv job for canvas_course_ids %s", args)
        try:
            mailing_lists = []
            canvas_course_ids = []
            if args:
                for ml in MailingList.objects.filter(canvas_course_id__in=args):
                    canvas_course_ids.append(ml.canvas_course_id)
                    mailing_lists.append(ml)
            else:
                for ml in MailingList.objects.all():
                    canvas_course_ids.append(ml.canvas_course_id)
                    mailing_lists.append(ml)

            logger.info("Synchronizing listserv mailing lists for canvas course ids %s", canvas_course_ids)

            sync_mailing_lists_with_listserv(mailing_lists)

            logger.info("Finished sync_listserv job for canvas_course_ids %s", canvas_course_ids)
        except Exception:
            message = "Error encountered while synchronizing mailing lists for canvas course ids %s" % canvas_course_ids
            logger.exception(message)
            raise CommandError(message)
