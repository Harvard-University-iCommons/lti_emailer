import logging

from django.core.management.base import BaseCommand

from mailgun.listserv_client import MailgunClient as ListservClient
from mailing_list.models import MailingList


OUTPUT_FIELDS = ['id', 'sis_course_id', 'name', 'course_code']

logger = logging.getLogger(__name__)

listserv_client = ListservClient()


class Command(BaseCommand):
    help = 'Sets access_level on all Mailgun mailing lists to read only'

    def handle(self, *args, **options):
        for ml in MailingList.objects.all():
            listserv_client.update_list(ml, 'readonly')
