import logging
import requests
import json

from django.conf import settings

from icommons_common.utils import grouper, ApiRequestTimer

from lti_emailer.exceptions import ListservApiError


logger = logging.getLogger(__name__)


class MailgunClient(object):
    """
    Listserv client for the Mailgun API
    https://documentation.mailgun.com/api_reference.html
    """

    @property
    def domain(self):
        return settings.LISTSERV_DOMAIN

    @property
    def api_url(self):
        return "%slists" % settings.LISTSERV_API_URL

    @property
    def api_user(self):
        return settings.LISTSERV_API_USER

    @property
    def api_key(self):
        return settings.LISTSERV_API_KEY

    def get_list(self, mailing_list):
        """
        Get the mailing_list from the listserv.

        :param mailing_list:
        :return: The listserv mailing list data dict.
        """
        address = mailing_list.address
        api_url = "%s/%s" % (self.api_url, address)

        with ApiRequestTimer(logger, 'GET', api_url) as timer:
            response = requests.get(api_url, auth=(self.api_user, self.api_key))
            timer.status_code = response.status_code

        if response.status_code not in (200, 404):
            logger.error(response.text)
            raise ListservApiError("Failed to get mailing lists from %s" % self.api_url)

        return response.json().get('list')

    def create_list(self, mailing_list, access_level='members'):
        """
        Create the mailing_list on the listserv.

        :param mailing_list:
        :param access_level:
        :return:
        """
        address = mailing_list.address
        payload = {
            'address': address,
            'access_level': access_level
        }

        with ApiRequestTimer(logger, 'POST', self.api_url, payload) as timer:
            response = requests.post(self.api_url, auth=(self.api_user, self.api_key), data=payload)
            timer.status_code = response.status_code

        if response.status_code != 200:
            message = "Response %d %s creating mailgun mailing list %s" % (response.status_code, response.text, address)
            logger.error(message)
            raise ListservApiError(message)

    def delete_list(self, mailing_list):
        """
        Delete the mailing_list from the listserv.

        :param mailing_list:
        :return:
        """
        address = mailing_list.address
        api_url = "%s/%s" % (self.api_url, address)

        with ApiRequestTimer(logger, 'DELETE', api_url) as timer:
            response = requests.delete(api_url, auth=(self.api_user, self.api_key))
            timer.status_code = response.status_code

        if response.status_code != 200:
            logger.error(response.text)
            raise ListservApiError("Failed to delete mailing list %s" % address)

    def update_list(self, mailing_list, access_level='members'):
        """
        Update the mailing list on the listserv.

        :param mailing_list:
        :param access_level:
        :return:
        """
        address = mailing_list.address
        api_url = "%s/%s" % (self.api_url, address)
        payload = {
            'access_level': access_level
        }

        with ApiRequestTimer(logger, 'PUT', api_url, payload) as timer:
            response = requests.put(api_url, auth=(self.api_user, self.api_key), data=payload)
            timer.status_code = response.status_code

        if response.status_code != 200:
            message = "Response %d %s updating mailgun mailing list %s" % (response.status_code, response.text, address)
            logger.error(message)
            raise ListservApiError(message)

    def members(self, mailing_list):
        """
        Get the mailing_list members from the listserv.

        :param mailing_list:
        :return: The list of members
        """
        address = mailing_list.address
        api_url = "%s/%s/members" % (self.api_url, mailing_list.address)

        # Mailgun limits the number of members returned to 100 per API call, so
        # we need to retrieve the members in batches of 100
        # Make a capped number of API calls to get all of the mailing list members
        result = []
        limit = 100
        for index in range(0, 100):
            url = "%s?limit=%d&skip=%d" % (api_url, limit, index * 100)

            with ApiRequestTimer(logger, 'GET', url) as timer:
                response = requests.get(url, auth=(self.api_user, self.api_key))
                timer.status_code = response.status_code

            if response.status_code != 200:
                logger.error(response.text)
                start = index * 100
                end = start + 100
                raise ListservApiError("Failed to get mailing list members %s range [%d-%d]" % (address, start, end))
            else:
                data = response.json()
                result += data['items']
                if len(result) >= data['total_count']:
                    # We have retrieved all members, so stop sending API requests
                    break

        return result

    def add_members(self, mailing_list, emails):
        """
        Adds the given emails as members to the mailing_list on the listserv.

        :param mailing_list:
        :param emails:
        :return:
        """
        address = mailing_list.address
        api_url = "%s/%s/members.json" % (self.api_url, address)

        # Mailgun limits the number of members which can be added in a single API POST to 1000, so
        # we have to add members in batches of 1000
        batches = grouper(emails, 1000)
        for index, batch in enumerate(batches):
            payload = {
                'members': json.dumps(batch),
                'upsert': 'yes'
            }

            with ApiRequestTimer(logger, 'POST', api_url, payload) as timer:
                response = requests.post(api_url, auth=(self.api_user, self.api_key), data=payload)
                timer.status_code = response.status_code

            if response.status_code != 200:
                logger.error(response.text)
                raise ListservApiError("Failed to add mailing list members batch %d of %d emails %s" % (
                    index + 1,
                    len(emails),
                    json.dumps(payload))
                )

    def delete_members(self, mailing_list, emails):
        """
        Deletes the given emails from the members list on the listserv.

        :param mailing_list:
        :param emails:
        :return:
        """
        address = mailing_list.address
        api_url = "%s/%s/members" % (self.api_url, address)

        for index, email in enumerate(emails):
            url = "%s/%s" % (api_url, email)

            with ApiRequestTimer(logger, 'DELETE', url) as timer:
                response = requests.delete(url, auth=(self.api_user, self.api_key))
                timer.status_code = response.status_code

            if response.status_code != 200:
                logger.error(response.text)
                raise ListservApiError("Failed to delete member %s from mailing_list %s %d of %d" % (
                    email,
                    address,
                    index,
                    len(emails)
                ))