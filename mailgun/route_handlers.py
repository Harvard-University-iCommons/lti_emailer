import logging

from django.http import JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from flanker.addresslib import address

from icommons_common.models import CourseInstance
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
    message_body = request.POST.get('body-plain')
    in_reply_to = request.POST.get('in-reply-to')
    logger.info("Handling Mailgun mailing list email from %s to %s", sender, recipient)
    if in_reply_to:
        # If it is a reply to the mailing list, extract the comma/semicolon separated addresses in the To/CC
        # fields to avoid duplicate being sent
        to_cc_list = (address.parse_list(request.POST.get('to')) 
                          + address.parse_list(request.POST.get('cc')))
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
    if ml.access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender not in member_addresses:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the sender was not a member",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_STAFF and sender not in teaching_staff_addresses:
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
            'message_body': message_body
        }))
        subject = "Undeliverable mail"
        ml.send_mail(sender, subject, html=content)
    else:
        # try to prepend [SHORT TITLE] to subject, keep going if lookup fails
        try:
            ci = CourseInstance.objects.get(canvas_course_id=ml.canvas_course_id)
        except CourseInstance.DoesNotExist:
            logger.warning(
                'Unable to find the course instance for Canvas course id {}, '
                'so we cannot prepend a short title to the email subject field.'
                .format(canvas_course_id))
        except CourseInstance.MultipleObjectsReturned:
            logger.warning(
                'Found multiple course instances for Canvas course id {}, '
                'so we cannot prepend a short title to the email subject field.'
                .format(canvas_course_id))
        except RuntimeError:
            logger.exception(
                'Received unexpected error trying to look up course instance '
                'for Canvas course id {}'.format(canvas_course_id))
        else:
            title_prefix = '[{}]'.format(ci.short_title)
            if title_prefix not in subject:
                subject = title_prefix + ' ' + subject

        # Do not send to the sender. Also check if it is a reply-all and do not send to users in the To/CC
        # if they are already in the mailing list - to avoid duplicates being sent as the email client would
        #  have already sent it
        try:
            member_addresses.remove(sender)
            if in_reply_to:
                logger.debug("Removing any duplicate addresses =%s from this message as it is a reply all"
                             % to_cc_list)
                member_addresses.difference_update(to_cc_list)
        except KeyError:
            logger.info("Email sent to mailing list %s from non-member address %s", ml.address, sender)

        # we want to add 'via Canvas' to the sender's name.  so first make
        # sure we know their name.
        sender_address = address.parse(sender)
        if sender_address.display_name:
            name = _get_name_for_email(sender_address.address)
            if name:
                sender_address.display_name = name

        # now add in 'via Canvas'
        if sender_address.display_name:
            sender_address.display_name += ' via Canvas'
        sender_address = sender_address.full_spec()

        # and send it off
        for member_address in member_addresses:
            ml.send_mail(sender_address, member_address, subject,
                         text=message_body)

    return JsonResponse({'success': True})


def _get_name_for_email(canvas_course_id, address):
    users = canvas_api_client.get_users_in_course(canvas_course_id)
    names_by_email = {u['email']: u['name'] for u in users}
    return names_by_email.get(address, '')
