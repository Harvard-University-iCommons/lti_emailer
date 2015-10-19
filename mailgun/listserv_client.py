import logging
import requests
import json

from django.conf import settings

from icommons_common.utils import ApiRequestTimer

from lti_emailer.exceptions import ListservApiError
from mailgun.utils import replace_non_ascii


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

    def send_mail(self, list_address, from_address, to_address, subject='',
                  text='', html='', original_to_address=None,
                  original_cc_address=None, attachments=None, inlines=None,
                  message_id=None):
        api_url = "%s%s/messages" % (settings.LISTSERV_API_URL,
                                     settings.LISTSERV_DOMAIN)
        payload = {
            'from': list_address,
            'h:List-Id': '<{}>'.format(list_address),
            'h:Reply-To': from_address,
            'html': html,
            'subject': subject,
            'text': text,
            'to': to_address,
        }

        # include the message-id header if we got it
        if message_id:
            payload['Message-Id'] = message_id

        # we want the to/cc fields as received by list users to be as close
        # as possible to the same as those that were sent by the sender.
        # mailgun will always add the individual recipient to the To field,
        # but we can at least ensure that's the only change.
        #
        # these are prefixed with h: so that mailgun doesn't think we want it
        # to send copies to these addresses as well.
        if original_to_address:
            payload['h:To'] = original_to_address
        if original_cc_address:
            payload['h:Cc'] = original_cc_address

        # we accept a single address or a list of addresses in to_address.
        # if it's a list, add in recipient_variables to make sure mailgun
        # doesn't include the whole list in the to: field, per
        #   https://documentation.mailgun.com/user_manual.html#batch-sending
        if not isinstance(to_address, basestring):
            recipient_variables = {e: {} for e in to_address}
            payload['recipient-variables'] = json.dumps(recipient_variables)

        # We need to replace non-ascii characters in attachment filenames
        # because Mailgun does not support RFC 2231
        # See http://stackoverflow.com/questions/24397418/python-requests-issues-with-non-ascii-file-names
        files = []
        if attachments:
            files.extend([('attachment', (replace_non_ascii(f.name), f, f.content_type)) for f in attachments])
        if inlines:
            files.extend([('inline', (replace_non_ascii(f.name), f, f.content_type)) for f in inlines])

        with ApiRequestTimer(logger, 'POST', api_url, payload) as timer:
            response = requests.post(api_url, auth=(self.api_user, self.api_key),
                                     data=payload, files=files)
            timer.status_code = response.status_code

        if response.status_code != 200:
            logger.error(
                u'Failed to POST email from %s to %s.  Status code was %s, body '
                u'was %s', from_address, to_address, response.status_code,
                response.text)
            raise ListservApiError(response.text)
