import logging
import requests
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %z'
EVENTS_MAX_PAGE_SIZE = 300
EVENTS_OF_INTEREST = ('accepted',)
SUBJECT = 'Undeliverable mail'

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Queries the Mailgun Events API with the given arguments'

    def add_arguments(self, parser):
        parser.add_argument('--begin', type=int, default=1443026760,
                            help='Epoch timestamp to begin log aggregation'
                                 '(default: %(default)s)')
        parser.add_argument('--end', type=int, default=1443038400,
                            help='Epoch timestamp to end log aggregation'
                                 '(default: %(default)s)')

    def handle(self, *args, **options):
        begin = options['begin']
        end = options['end']
        logger.info('Pulling events from {} to {} for {}'.format(begin, end, settings.LISTSERV_DOMAIN))
        events = self.get_events(begin, end)
        logger.debug('Done pulling events')
        self.process_events(events)

    def get_events(self, begin, end):
        # prime the pump
        url = '{}{}/events'.format(settings.LISTSERV_API_URL,
                                   settings.LISTSERV_DOMAIN)
        auth = (settings.LISTSERV_API_USER, settings.LISTSERV_API_KEY)
        params = {
            'begin': begin,
            'end': end,
            'limit': EVENTS_MAX_PAGE_SIZE,
            'event': ' OR '.join(EVENTS_OF_INTEREST),
            # 'subject': SUBJECT,
        }
        try:
            resp = requests.get(url, auth=auth, params=params)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise CommandError(str(e))
        events = resp.json()['items']

        # follow 'next' links until we get a blank page
        while True:
            url = resp.json()['paging']['next']
            try:
                resp = requests.get(url, auth=auth)
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
        count = 0
        for event in events:
            # if 'canvas-4395-8694@coursemail.harvard.edu' in event['message']['headers']['from']:
            # if 'canvas-4779-6168@coursemail.harvard.edu' in event['message']['headers']['from']:
            # if 'canvas-3958-7530@coursemail.harvard.edu' in event['message']['headers']['from']:
            if 'canvas-2043-13874@coursemail.harvard.edu' in event['message']['headers']['from']:
                count += 1
                self.stdout.write(json.dumps(event, indent=4))
        self.stdout.write("{} events".format(count))
