import argparse
import csv
import datetime
import logging
import requests
import sys
from collections import defaultdict

import pytz
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from mailgun.management.commands._mailgun_api import get_events


EVENTS_OF_INTEREST = ('accepted',)

logger = logging.getLogger(__name__)
utc = pytz.timezone('UTC')


class Command(BaseCommand):
    help = '''Prints a list of emails sent in a given time window'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--begin-time', type=int, required=True,
            help='Beginning of the window to look for emails, as unix timestamp')
        parser.add_argument(
            '--end-time', type=int, required=True,
            help='End of the window to look for emails, as unix timestamp')
        parser.add_argument(
            '--output-file', type=argparse.FileType('w'), default=sys.stdout,
            help='File to output the csv of emails sent to, defaults to stdout')

    def handle(self, *args, **options):
        begin = datetime.datetime.fromtimestamp(options['begin_time'], utc)
        end = datetime.datetime.fromtimestamp(options['end_time'], utc)

        events = get_events(begin, end, EVENTS_OF_INTEREST)
        self.process_events(events, options['output_file'])

    def process_events(self, events, output_file):
        rows = []
        for event in events:
            try:
                sender = event['envelope']['sender']
            except RuntimeError:
                logger.exception('event {} missing a sender'.format(event))
                continue

            if sender.endswith(settings.LISTSERV_DOMAIN):
                continue

            try:       
                list_address = None
                for recipient in event['message']['recipients']:
                    if (settings.LISTSERV_SECTION_ADDRESS_RE.match(recipient)
                            or settings.LISTSERV_COURSE_ADDRESS_RE.match(recipient)):
                        list_address = recipient
                        break

                row = [
                    float(event['timestamp']),
                    list_address,
                    sender,
                    event['message']['headers']['subject'],
                    event['message']['headers']['message-id']
                ]
            except KeyError as e:
                logger.error('Unable to extract {} from event'.format(e.args[0]))
            else:
                rows.append(row)
        rows.sort()

        headers = ('timestamp', 'list', 'sender', 'subject', 'message-id')
        writer = csv.writer(output_file)
        writer.writerow(headers)
        writer.writerows(rows)
