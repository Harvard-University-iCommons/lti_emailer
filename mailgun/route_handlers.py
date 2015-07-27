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
    logger.info("Handling Mailgun mailing list email from %s to %s", sender, recipient)
    try:
        ml = MailingList.objects.get_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        message = "Could not find MailingList for email address %s" % recipient
        logger.error(message)
        return JsonResponse({'error': message}, status=406)  # Return status 406 so Mailgun does not retry

    member_addresses = [m['address'] for m in ml.members]
    bounce_back_email_template = None
    if ml.access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender not in member_addresses:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the sender was not a member",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_access_denied.html')
    elif ml.access_level == MailingList.ACCESS_LEVEL_STAFF and sender not in ml.teaching_staff_addresses:
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
        # Send the email to the mailing list members and teaching staff
        addresses = set(member_addresses + ml.teaching_staff_addresses)
        for address in addresses:
            ml.send_mail(address, subject, text=message_body)

    return JsonResponse({'success': True})
