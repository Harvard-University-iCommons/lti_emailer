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
INPUT_DATETIME_FORMAT = '%Y%m%d%H%M%S'
OUTPUT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S  %Z%z'
TZ = pytz.timezone('US/Eastern') # can't rely on settings, it's usually UTC
UTC = pytz.timezone('UTC')

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Prints a list of emails sent in a given time window'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--begin-time', type=_datetime, required=True,
            help='Beginning of the window to look for emails, formatted as '
                 'YYYYMMDDHHMMSS')
        parser.add_argument(
            '--end-time', type=_datetime, required=True,
            help='End of the window to look for emails, formatted as '
                 'YYYYMMDDHHMMSS')
        parser.add_argument(
            '--output-file', type=argparse.FileType('w'), default=sys.stdout,
            help='File to output the csv of emails sent to, defaults to stdout')

    def handle(self, *args, **options):
        events = get_events(options['begin_time'], options['end_time'],
                            EVENTS_OF_INTEREST)
        self.process_events(events, options['output_file'])

    def process_events(self, events, output_file):
        rows = []
        for event in events:
            try:
                sender = event['envelope']['sender']
            except RuntimeError:
                logger.exception('event {} missing a sender'.format(event))
                continue

            # skip events where we're forwarding mail to the list
            if sender.endswith(settings.LISTSERV_DOMAIN):
                continue

            try:       
                list_address = None
                for recipient in event['message']['recipients']:
                    if (settings.LISTSERV_SECTION_ADDRESS_RE.match(recipient)
                            or settings.LISTSERV_COURSE_ADDRESS_RE.match(recipient)):
                        list_address = recipient
                        break

                timestamp = datetime.datetime.fromtimestamp(event['timestamp'], UTC)
                timestamp = timestamp.astimezone(TZ).strftime(OUTPUT_DATETIME_FORMAT)
                row = [
                    timestamp,
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


def _datetime(arg):
    dt = datetime.datetime.strptime(arg, INPUT_DATETIME_FORMAT)
    return TZ.localize(dt)
