import json
import logging
import re

from django.http import JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from flanker.addresslib import address

from icommons_common.models import CourseInstance

from lti_emailer.canvas_api_client import get_name_for_email
from mailgun.decorators import authenticate
from mailgun.listserv_client import MailgunClient as ListservClient
from mailing_list.models import MailingList


logger = logging.getLogger(__name__)

listserv_client = ListservClient()


@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
def handle_mailing_list_email_route(request):
    '''
    Handles the Mailgun route action when email is sent to a Mailgun mailing list.
    1. Verify that recipient address is a course mailing list
    2. If access level of mailing list is 'members' and sender is not a member, send email response notifying the sender
    that their email was not received because they are not a member of the list
    3. If access level of mailing list is 'readonly', send email response notifying the sender that their email was not
    received because the list is currently not accepting email from anyone
    4. Verify if user can post to the list: If access level of mailing list is 'staff' and sender is not enrolled as a
    teacher, the mail should not be sent
    :param request:
    :return:
    '''
    sender = request.POST.get('sender')
    recipient = request.POST.get('recipient')
    subject = request.POST.get('subject')
    body_plain = request.POST.get('body-plain', '')
    body_html = request.POST.get('body-html', '')
    to_list = address.parse_list(request.POST.get('To'))
    cc_list = address.parse_list(request.POST.get('Cc'))

    attachments, inlines = _get_attachments_inlines(request)

    logger.info(u'Handling Mailgun mailing list email from %s to %s',
                sender, recipient)
    logger.debug(u'Full mailgun post: %s', request.POST)

    # if we want to check email addresses against the sender, we need to parse
    # out just the address.
    parsed_sender = address.parse(sender)
    sender_address = parsed_sender.address.lower()
    sender_display_name = parsed_sender.display_name

    # make sure the mailing list exists
    bounce_back_email_template = None
    try:
        ml = MailingList.objects.get_or_create_or_delete_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        logger.info(
            u'Sending mailing list bounce back email to %s for mailing list %s '
            u'because the mailing list does not exist', sender, recipient)
        bounce_back_email_template = get_template('mailgun/email/bounce_back_does_not_exist.html')
        content = bounce_back_email_template.render(Context({
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'message_body': body_plain or body_html,
        }))
        listserv_client.send_mail(recipient, recipient, sender_address,
                                  subject='Undeliverable mail', html=content)
        return JsonResponse({'success': True})

    # Always include teaching staff addresses with members addresses, so that they can email any list in the course
    teaching_staff_addresses = ml.teaching_staff_addresses
    member_addresses = teaching_staff_addresses.union([m['address'] for m in ml.members])
    if ml.access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender_address not in member_addresses:
        logger.info(
            u'Sending mailing list bounce back email to %s for mailing list %s '
            u'because the sender was not a member', sender, recipient)
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_STAFF and sender_address not in teaching_staff_addresses:
        logger.info(
            u'Sending mailing list bounce back email to %s for mailing list %s '
            u'because the sender was not a staff member', sender, recipient)
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_READONLY:
        logger.info(
            u'Sending mailing list bounce back email to %s for mailing list %s '
            u'because the list is readonly', sender, recipient)
        bounce_back_email_template = get_template('mailgun/email/bounce_back_readonly_list.html')

    if bounce_back_email_template:
        content = bounce_back_email_template.render(Context({
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'message_body': body_plain or body_html,
        }))
        subject = 'Undeliverable mail'
        ml.send_mail('', ml.address, sender_address, subject=subject,
                     html=content)
    else:
        # try to prepend [SHORT TITLE] to subject, keep going if lookup fails
        try:
            ci = CourseInstance.objects.get(canvas_course_id=ml.canvas_course_id)
        except CourseInstance.DoesNotExist:
            logger.warning(
                u'Unable to find the course instance for Canvas course id %s, '
                u'so we cannot prepend a short title to the email subject.',
                ml.canvas_course_id)
        except CourseInstance.MultipleObjectsReturned:
            logger.warning(
                u'Found multiple course instances for Canvas course id %s, '
                u'so we cannot prepend a short title to the email subject.',
                ml.canvas_course_id)
        except RuntimeError:
            logger.exception(
                u'Received unexpected error trying to look up course instance '
                u'for Canvas course id %s', ml.canvas_course_id)
        else:
            if ci.short_title:
                title_prefix = '[{}]'.format(ci.short_title)
                if title_prefix not in subject:
                    subject = title_prefix + ' ' + subject

        # anyone in the to/cc field will already have gotten a copy of this
        # email directly from the sender.  let's not send them a duplicate.
        # let's also not send a copy to the sender.
        logger.debug(u'Full list of recipients: %s', member_addresses)
        try:
            logger.debug(u'Removing sender %s from the list of recipients',
                         sender_address)
            member_addresses.remove(sender_address)
        except KeyError:
            logger.info(
                u'Email sent to mailing list %s from non-member address %s',
                ml.address, sender)
        to_cc_list = {a.address for a in (to_list + cc_list)}
        logger.debug(
            u'Removing anyone in the to/cc list %s from the list of recipients',
            list(to_cc_list))
        member_addresses.difference_update(to_cc_list)
        member_addresses = list(member_addresses)
        logger.info(u'Final list of recipients: %s', member_addresses)

        # double check to make sure the list is in the to/cc field somewhere,
        # add it to cc if not.  do this to ensure that, even if someone decided
        # to bcc the list, it will be possible to reply-all to the list.
        if ml.address not in to_cc_list:
            cc_list.append(address.parse(ml.address))

        # we want to add 'via Canvas' to the sender's name.  so first make
        # sure we know their name.
        logger.debug(u'Original sender name: %s, address: %s',
                     sender_display_name, sender_address)
        if not sender_display_name:
            name = get_name_for_email(ml.canvas_course_id, sender_address)
            if name:
                sender_display_name = name
                logger.debug(u'Looked up sender name: %s, address: %s',
                             sender_display_name, sender_address)

        # now add in 'via Canvas'
        if sender_display_name:
            sender_display_name += ' via Canvas'
        logger.debug(u'Final sender name: %s, address: %s',
                     sender_display_name, sender_address)

        # make sure inline images actually show up inline, since fscking
        # mailgun won't let us specify the cid on post.  see their docs at
        #   https://documentation.mailgun.com/user_manual.html#sending-via-api
        # where they explain that they use the inlined file's name attribute
        # as the content-id.
        if inlines:
            for f in inlines:
                logger.debug(u'Replacing "%s" with "%s" in body', f.cid, f.name)
                body_plain = re.sub(f.cid, f.name, body_plain)
                body_html = re.sub(f.cid, f.name, body_html)

        # convert the original to/cc fields back to strings so we can send
        # them along through the listserv
        to_list = [a.full_spec() for a in to_list]
        cc_list = [a.full_spec() for a in cc_list]

        # and send it off
        logger.debug(
            u'Mailgun router handler sending email to %s from %s, subject %s',
            member_addresses, parsed_sender.full_spec(), subject)
        try:
            ml.send_mail(
                sender_display_name, sender_address,
                member_addresses, subject, text=body_plain, html=body_html,
                original_to_address=to_list, original_cc_address=cc_list,
                attachments=attachments, inlines=inlines
            )
        except RuntimeError:
            logger.exception(
                u'Error attempting to send message from %s to %s, originally '
                u'sent to list %s, with subject %s', parsed_sender.full_spec(),
                member_addresses, ml.address, subject)
            return JsonResponse({'success': False}, status=500)

    return JsonResponse({'success': True})


def _get_attachments_inlines(request):
    attachments = []
    inlines = []

    try:
        attachment_count = int(request.POST.get('attachment-count', 0))
    except RuntimeError:
        logger.exception(
            u'Unable to determine if there were attachments to this email')
        attachment_count = 0

    try:
        content_id_map = json.loads(request.POST.get('content-id-map', '{}'))
    except RuntimeError:
        logger.exception(u'Unable to find content-id map in this email, '
                         u'forwarding all files as attachments.')
        content_id_map = {}
    attachment_name_to_cid = {v: k.strip('<>')
                                  for k, v in content_id_map.iteritems()}
    logger.debug(u'Attachment name to cid: %s', attachment_name_to_cid)

    for n in xrange(1, attachment_count + 1):
        attachment_name = 'attachment-{}'.format(n)
        file_ = request.FILES[attachment_name]
        if attachment_name in attachment_name_to_cid:
            file_.cid = attachment_name_to_cid[attachment_name]
            file_.name = file_.name.replace(' ', '_')
            inlines.append(file_)
        else:
            attachments.append(file_)

    return attachments, inlines
