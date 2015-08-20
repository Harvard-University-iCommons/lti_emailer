import argparse
import datetime
import logging
import requests
from collections import defaultdict

import pytz
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %z'
EVENTS_MAX_PAGE_SIZE = 300
EVENTS_OF_INTEREST = ('accepted', 'delivered')

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Prints average and max delivery time for email sent in the past '
            'N days.')

    def add_arguments(self, parser):
        parser.add_argument('--days-back', type=int, default=7,
                            help='Number of days back to look at emails sent. '
                                 '(default: %(default)s)')

    def handle(self, *args, **options):
        end = datetime.datetime.now(tz=pytz.utc)
        begin = end - datetime.timedelta(days=options['days_back'])
        logger.info('Pulling {} days of events for {}'.format(
                        options['days_back'], settings.LISTSERV_DOMAIN))
        events = self.get_events(begin, end)
        logger.debug('Done pulling events')
        self.process_events(events)

    def get_events(self, begin, end):
        # prime the pump
        url = '{}{}/events'.format(settings.LISTSERV_API_URL,
                                   settings.LISTSERV_DOMAIN)
        auth = (settings.LISTSERV_API_USER, settings.LISTSERV_API_KEY)
        params = {
            'begin': begin.strftime(DATE_FORMAT),
            'end': end.strftime(DATE_FORMAT),
            'limit': EVENTS_MAX_PAGE_SIZE,
            'event': ' OR '.join(EVENTS_OF_INTEREST),
        }
        resp = requests.get(url, auth=auth, params=params)
        try:
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise CommandError(str(e))
        events = resp.json()['items']

        # follow 'next' links until we get a blank page
        while True:
            url = resp.json()['paging']['next']
            resp = requests.get(url, auth=auth)
            try:
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise CommandError(str(e))
            page = resp.json()['items']
            if len(page) == 0:
                break
            else:
                events.extend(page)
        return events

    def process_events(self, events):
        times = defaultdict(dict)
        for event in events:
            try:
                message_id = event['message']['headers']['message-id']
                times[event['event']][message_id] = event['timestamp']
            except KeyError:
                pass

        delivered_count = 0
        undelivered_count = 0
        total_delivery_time = 0.0
        max_time = 0.0
        for message_id in times['accepted']:
            if message_id in times['delivered']:
                delivered_count += 1
                delivery_time = (times['delivered'][message_id]
                                  - times['accepted'][message_id])
                total_delivery_time += delivery_time
                if delivery_time > max_time:
                    max_time = delivery_time
            else:
                undelivered_count += 1
        
        total_accepted = delivered_count + undelivered_count
        try:
            average_time = int(round(total_delivery_time / delivered_count))
        except ZeroDivisionError:
            average_time = 0
        max_time = int(round(max_time))
        self.stdout.write('Total emails accepted:  {}'.format(total_accepted))
        self.stdout.write('Total emails delivered: {}'.format(delivered_count))
        self.stdout.write('Average delivery time:  {} sec'.format(average_time))
        self.stdout.write('Max delivery time:      {} sec'.format(max_time))
