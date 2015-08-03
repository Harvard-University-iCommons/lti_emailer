import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.template.loader import get_template
from django.template import Context

from mailing_list.models import MailingList

from mailgun.decorators import authenticate


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
    in_reply_to = request.POST.get('In-Reply-To')
    logger.info("Handling Mailgun mailing list email from %s to %s", sender, recipient)
    if in_reply_to:
        original_to_address = request.POST.get('To')
        logger.debug("This is a reply!! in_reply_to=%s and original_to_address=%s" % (in_reply_to,original_to_address))

    try:
        ml = MailingList.objects.get_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        message = "Could not find MailingList for email address %s" % recipient
        logger.error(message)
        return JsonResponse({'error': message}, status=406)  # Return status 406 so Mailgun does not retry

    # Always include teaching staff addresses with members addresses, so that they can email any list in the course
    teaching_staff_addresses = ml.teaching_staff_addresses
    member_addresses = set([m['address'] for m in ml.members] + teaching_staff_addresses)
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
        # Do not send to the sender and also check if it is a reply-all and do not send to original sender to avoid
        # duplicate being sent as the email client would have already sent it per the Reply-To param set in header
        try:
            member_addresses.remove(sender)
            if in_reply_to:
                member_addresses.remove(original_to_address)
                logger.debug(" Removing original_to_address =%s from this message as it is a reply"
                             % original_to_address)
        except KeyError:
            logger.info("Email sent to mailing list %s from non-member address %s", ml.address, sender)

        for address in member_addresses:
            ml.send_mail(sender, address, subject, text=message_body)

    return JsonResponse({'success': True})
