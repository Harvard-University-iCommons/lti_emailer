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
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, address)

        with ApiRequestTimer(logger, 'GET', api_url) as timer:
            response = requests.get(api_url, auth=(self.api_user, self.api_key))
            timer.status_code = response.status_code

        if response.status_code not in (200, 404):
            logger.error(response.text)
            raise ListservApiError("Failed to get mailing lists from %s" % api_url)

        return response.json().get('list')

    def create_list(self, mailing_list, access_level='readonly'):
        """
        Create the mailing_list on the listserv.

        :param mailing_list:
        :param access_level:
        :return:
        """
        address = mailing_list.address
        api_url = "%slists" % settings.LISTSERV_API_URL
        payload = {
            'address': address,
            'access_level': access_level
        }

        with ApiRequestTimer(logger, 'POST', api_url, payload) as timer:
            response = requests.post(api_url, auth=(self.api_user, self.api_key), data=payload)
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
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, address)

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
        api_url = "%slists/%s" % (settings.LISTSERV_API_URL, address)
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
        api_url = "%slists/%s/members" % (settings.LISTSERV_API_URL, mailing_list.address)

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
        api_url = "%slists/%s/members.json" % (settings.LISTSERV_API_URL, address)

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
        api_url = "%slists/%s/members" % (settings.LISTSERV_API_URL, address)

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

    def send_mail(self, from_address, reply_to_address, to_address, cc_address,
                  subject='', text='', html='', attachments=None, inlines=None):
        api_url = "%s%s/messages" % (settings.LISTSERV_API_URL,
                                     settings.LISTSERV_DOMAIN)
        payload = {
            'from': from_address,
            'sender': from_address,
            'h:Reply-To': reply_to_address,
            'to': to_address,
            'h:cc': cc_address,
            'subject': subject,
            'text': text,
            'html': html
        }

        files = []
        if attachments:
            files.extend([('attachment', (f.name, f, f.content_type))
                              for f in attachments])
        if inlines:
            for f in inlines:
                files.append(('inline', (f.name, f, f.content_type,
                                         {'Content-ID': f.cid})))

        with ApiRequestTimer(logger, 'POST', api_url, payload) as timer:
            response = requests.post(api_url, auth=(self.api_user, self.api_key),
                                     data=payload, files=files)
            timer.status_code = response.status_code

        if response.status_code != 200:
            message = "Failed to POST email to Mailgun from %s to %s" % (from_address, to_address)
            logger.error(message)
            raise ListservApiError(message)
