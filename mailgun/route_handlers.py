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
from mailing_list.models import MailingList


logger = logging.getLogger(__name__)


@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
def handle_mailing_list_email_route(request):
    """
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
    """
    sender = request.POST.get('sender')
    recipient = request.POST.get('recipient')
    subject = request.POST.get('subject')
    body_plain = request.POST.get('body-plain')
    body_html = request.POST.get('body-html')
    in_reply_to = request.POST.get('In-Reply-To')

    attachments, inlines = _get_attachments_inlines(request)

    logger.info("Handling Mailgun mailing list email from %s to %s", sender, recipient)
    logger.debug('Full mailgun post: {}'.format(request.POST))

    # if we want to check email addresses against the sender, we need to parse
    # out just the address.
    sender_address = address.parse(sender)

    if in_reply_to:
        # If it is a reply to the mailing list, extract the comma/semicolon separated addresses in the To/CC
        # fields to avoid duplicate being sent
        logger.debug("This is a reply!! in_reply_to=%s ", in_reply_to)
        to_cc_list = (address.parse_list(request.POST.get('To')) + address.parse_list(request.POST.get('Cc')))
        to_cc_list = [a.address for a in to_cc_list]
    try:
        ml = MailingList.objects.get_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        message = "Could not find MailingList for email address %s" % recipient
        logger.error(message)
        return JsonResponse({'error': message}, status=406)  # Return status 406 so Mailgun does not retry

    # Always include teaching staff addresses with members addresses, so that they can email any list in the course
    teaching_staff_addresses = ml.teaching_staff_addresses
    member_addresses = teaching_staff_addresses.union([m['address'] for m in ml.members])
    bounce_back_email_template = None
    if ml.access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender_address.address not in member_addresses:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the sender was not a member",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_STAFF and sender_address.address not in teaching_staff_addresses:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the sender "
            "was not a staff member",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_READONLY:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the list is readonly",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_readonly_list.html')

    if bounce_back_email_template:
        content = bounce_back_email_template.render(Context({
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'message_body': body_plain or body_html,
        }))
        subject = "Undeliverable mail"
        ml.send_mail('', ml.address, sender_address.address, subject, html=content)
    else:
        # try to prepend [SHORT TITLE] to subject, keep going if lookup fails
        try:
            ci = CourseInstance.objects.get(canvas_course_id=ml.canvas_course_id)
        except CourseInstance.DoesNotExist:
            logger.warning(
                'Unable to find the course instance for Canvas course id {}, '
                'so we cannot prepend a short title to the email subject field.'
                .format(ml.canvas_course_id))
        except CourseInstance.MultipleObjectsReturned:
            logger.warning(
                'Found multiple course instances for Canvas course id {}, '
                'so we cannot prepend a short title to the email subject field.'
                .format(ml.canvas_course_id))
        except RuntimeError:
            logger.exception(
                'Received unexpected error trying to look up course instance '
                'for Canvas course id {}'.format(ml.canvas_course_id))
        else:
            if ci.short_title:
                title_prefix = '[{}]'.format(ci.short_title)
                if title_prefix not in subject:
                    subject = title_prefix + ' ' + subject

        # Do not send to the sender. Also check if it is a reply-all and do not send to users in the To/CC
        # if they are already in the mailing list - to avoid duplicates being sent as the email client would
        #  have already sent it
        logger.debug('Full list of recipients: {}'.format(member_addresses))
        try:
            member_addresses.remove(sender_address.address)
            if in_reply_to:
                logger.debug('Removing any duplicate addresses =%s from this '
                             'message as it is a reply all'
                             % to_cc_list)
                member_addresses.difference_update(to_cc_list)
        except KeyError:
            logger.info("Email sent to mailing list %s from non-member address %s", ml.address, sender)

        # we want to add 'via Canvas' to the sender's name.  so first make
        # sure we know their name.
        logger.debug(
            'Original sender name: {}, address: {}'.format(sender_address.display_name, sender_address.address)
        )
        if not sender_address.display_name:
            name = get_name_for_email(ml.canvas_course_id, sender_address.address)
            if name:
                sender_address.display_name = name
                logger.debug(
                    'Looked up sender name: {}, address: {}'.format(sender_address.display_name, sender_address.address)
                )

        # now add in 'via Canvas'
        if sender_address.display_name:
            sender_address.display_name += ' via Canvas'
        logger.debug('Final sender name: {}, address: {}'.format(sender_address.display_name, sender_address.address))

        # make sure inline images actually show up inline, since fscking
        # mailgun won't let us specify the cid on post.  see their docs at
        #   https://documentation.mailgun.com/user_manual.html#sending-via-api
        # where they explain that they use the inlined file's name attribute
        # as the content-id.
        if inlines:
            for f in inlines:
                logger.debug('Replacing "{}" with "{}" in body'.format(f.cid,
                                                                       f.name))
                body_plain = re.sub(f.cid, f.name, body_plain)
                body_html = re.sub(f.cid, f.name, body_html)

        # and send it off
        logger.info('Final list of recipients: {}'.format(member_addresses))
        logger.debug(
            "Mailgun router handler sending email to {} from {}, subject {}".format(
                member_addresses, sender_address.full_spec(), subject
            )
        )
        ml.send_mail(
            sender_address.display_name, sender_address.address,
            list(member_addresses), subject, text=body_plain, html=body_html,
            attachments=attachments, inlines=inlines
        )

    return JsonResponse({'success': True})


def _get_attachments_inlines(request):
    attachments = []
    inlines = []

    try:
        attachment_count = int(request.POST.get('attachment-count', 0))
    except RuntimeError:
        logger.exception('Unable to determine if there were attachments to '
                         'this email')
        attachment_count = 0

    try:
        content_id_map = json.loads(request.POST.get('content-id-map', '{}'))
    except RuntimeError:
        logger.exception('Unable to find content-id map in this email, '
                         'forwarding all files as attachments.')
        content_id_map = {}
    attachment_name_to_cid = {v: k.strip('<>')
                                  for k,v in content_id_map.iteritems()}
    logger.debug('Attachment name to cid: {}'.format(attachment_name_to_cid))

    for n in xrange(1, attachment_count+1):
        attachment_name = 'attachment-{}'.format(n)
        file_ = request.FILES[attachment_name]
        if attachment_name in attachment_name_to_cid:
            file_.cid = attachment_name_to_cid[attachment_name]
            file_.name = file_.name.replace(' ', '_')
            inlines.append(file_)
        else:
            attachments.append(file_)

    return attachments, inlines
