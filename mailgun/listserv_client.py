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
                  eml_attachments=None, message_id=None):
        api_url = "%s%s/messages" % (settings.LISTSERV_API_URL,
                                     settings.LISTSERV_DOMAIN)

        logger.debug(f'send_mail called with list_address={list_address} ' 
                     f'from_address={from_address} to_address={to_address} '
                     f'subject={subject} original_to_address={original_to_address} '
                     f'original_cc_address={original_cc_address} message_id={message_id}')

        payload = {
            'from': list_address,
            'h:List-Id': '<{}>'.format(list_address),
            'h:Reply-To': from_address,
            'html': html,
            'subject': subject,
            'text': text,
            'to': to_address,
        }

        # mailgun rejects emails with empty text and html bodies.  if both
        # are empty, use a single space as the text body to work around that.
        if not html and not text:
            payload['text'] = ' '

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
        cc_list = []

        if original_to_address:
            cc_list.extend(original_to_address)

        if original_cc_address:
            cc_list.extend(original_cc_address)

        if cc_list:
            payload['h:cc'] = ','.join(cc_list)

        # we accept a single address or a list of addresses in to_address.
        # if it's a list, add in recipient_variables to make sure mailgun
        # doesn't include the whole list in the to: field, per
        #   https://documentation.mailgun.com/user_manual.html#batch-sending
        if not isinstance(to_address, str):
            # the recipient variables aren't actually used, so we just send a fake dict
            recip_var_dict = {'k': 'v'}
            recipient_variables = {e: recip_var_dict for e in to_address}
            payload['recipient-variables'] = json.dumps(recipient_variables)

        # We need to replace non-ascii characters in attachment filenames
        # because Mailgun does not support RFC 2231
        # See http://stackoverflow.com/questions/24397418/python-requests-issues-with-non-ascii-file-names
        files = []
        if attachments:
            files.extend([('attachment', (replace_non_ascii(f.name), f, f.content_type)) for f in attachments])
        if inlines:
            files.extend([('inline', (replace_non_ascii(f.name), f, f.content_type)) for f in inlines])
        
        if eml_attachments:
            payload.update(eml_attachments)

        logger.info(f'Payload data: ', extra=payload)

        with ApiRequestTimer(logger, 'POST', api_url, payload) as timer:
            response = requests.post(api_url, auth=(self.api_user, self.api_key),
                                     data=payload, files=files)
            timer.status_code = response.status_code

        if response.status_code != 200:
            logger.error(
                'Failed to POST email from %s to %s.  Status code was %s, body '
                'was %s', from_address, to_address, response.status_code,
                response.text)
            raise ListservApiError(response.text)
