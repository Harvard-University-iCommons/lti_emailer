import datetime
import logging
import requests

from django.conf import settings


DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %z'
EVENTS_MAX_PAGE_SIZE = 300

logger = logging.getLogger(__name__)


def get_events(begin, end, event_types):
    # prime the pump
    url = '{}{}/events'.format(settings.LISTSERV_API_URL,
                               settings.LISTSERV_DOMAIN)
    auth = (settings.LISTSERV_API_USER, settings.LISTSERV_API_KEY)
    params = {
        'begin': begin.strftime(DATE_FORMAT),
        'end': end.strftime(DATE_FORMAT),
        'limit': EVENTS_MAX_PAGE_SIZE,
        'event': ' OR '.join(event_types),
    }
    resp = requests.get(url, auth=auth, params=params)
    resp.raise_for_status()
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
