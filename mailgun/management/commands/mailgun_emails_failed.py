import argparse
import csv
import datetime
import json
import logging
import sys

import pytz
from django.conf import settings
from django.core.management.base import BaseCommand

from mailgun.management.commands._mailgun_api import get_events

EVENTS_OF_INTEREST = ('failed',)
INPUT_DATETIME_FORMAT = '%Y%m%d%H%M%S'
OUTPUT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S  %Z%z'
TZ = pytz.timezone('US/Eastern') # can't rely on settings, it's usually UTC
UTC = pytz.timezone('UTC')

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Prints a list of emails with permanent failures in a given time '
            'window')

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
        parser.add_argument(
            '--include-temporary', action='store_true', default=False,
            help='Include temporary failures, defaults to False')

    def handle(self, *args, **options):
        filter_kwargs = {'severity': 'permanent'}
        if options['include_temporary']:
            filter_kwargs['severity'] += ' OR temporary'
        events = get_events(options['begin_time'], options['end_time'],
                            EVENTS_OF_INTEREST, **filter_kwargs)
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
                logger.error(
                    'Unexpectedly received a failure event for the mailer '
                    'sending to a user:\n%s', json.dumps(event))
                continue

            try:       
                timestamp = datetime.datetime.fromtimestamp(event['timestamp'], UTC)
                timestamp = timestamp.astimezone(TZ).strftime(OUTPUT_DATETIME_FORMAT)
                list_addresses = [a for a in event['message']['recipients']
                                      if a.endswith(settings.LISTSERV_DOMAIN)]
                list_address = ';'.join(list_addresses)
                row = (
                    timestamp,
                    list_address,
                    sender,
                    event['message']['headers']['subject'],
                    event['message']['headers']['message-id'],
                )
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
