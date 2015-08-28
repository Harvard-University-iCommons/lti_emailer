import logging

from optparse import make_option

from django.core.management.base import BaseCommand

from mailgun.listserv_client import MailgunClient as ListservClient
from mailing_list.models import MailingList


OUTPUT_FIELDS = ['id', 'sis_course_id', 'name', 'course_code']

logger = logging.getLogger(__name__)

listserv_client = ListservClient()


class Command(BaseCommand):
    help = 'Sets access_level on all Mailgun mailing lists to read only'
    option_list = BaseCommand.option_list + (
        make_option(
            '--fake',
            action='store_true',
            dest='fake',
            default=False,
            help='Only log the mailing lists that are not readonly'
        ),
    )

    def handle(self, *args, **options):
        non_readonly = []
        for ml in MailingList.objects.all():
            l = listserv_client.get_list(ml)
            if l['access_level'] != 'readonly':
                non_readonly.append(l)
                if not options['fake']:
                    listserv_client.update_list(ml, 'readonly')
        for l in non_readonly:
            logger.info(l)
        logger.info("Found %d non-readonly lists and set them to readonly", len(non_readonly))
