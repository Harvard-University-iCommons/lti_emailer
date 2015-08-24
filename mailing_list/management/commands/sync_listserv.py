import logging

from django.core.management.base import BaseCommand

from mailing_list.tasks import course_sync_listserv


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronizes mailing lists created for canvas courses with the enrollment list for each course'

    def handle(self, *args, **options):
        logger.info("Beginning sync_listserv job for canvas_course_ids %s", args)
        course_sync_listserv(args or None)
