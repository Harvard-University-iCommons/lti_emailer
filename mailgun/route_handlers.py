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
    if ml.get_listserv_access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender not in member_addresses:
        logger.info(
            "Sending mailing list bounce back email to %s for mailing list %s because the sender was not a member",
            sender,
            recipient
        )
        bounce_back_email_template = get_template('mailgun/email/bounce_back_non_member.html')
    elif ml.get_listserv_access_level == MailingList.ACCESS_LEVEL_READONLY:
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

    return JsonResponse({'success': True})




@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
def handle_outgoing_emails_route(request):
    """
    Handles the Mailgun route action when email is sent to any Mailgun mailing list.
    1. Check the access level for the mailing list to see if it is set to 'staff'
    2. Verify if user can post to the list: If access level of mailing list is 'staff' and sender is not a  course staff
     member, the mail should not be sent

    :param request:
    :return:
    """
    sender = request.POST.get('sender')
    recipient = request.POST.get('recipient')
    subject = request.POST.get('subject')
    message_body = request.POST.get('body-plain')
    logger.info("Handling Mailgun outgoing mailing list email from %s to %s", sender, recipient)

    # fetch the mailing list access level
    try:
        ml = MailingList.objects.get_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        message = "Could not find MailingList for email address %s" % recipient
        logger.error(message)
        return JsonResponse({'error': message}, status=406)  # Return status 406 so Mailgun does not retry

    mailing_list_access_level = ml.acess.level
    logger.debug(" in router, mailing_list_access_level set to %s" % mailing_list_access_level)

    # if the access level is set to  MailingList.ACCESS_LEVEL_STAFF, verify that sender is a staff
    if mailing_list_access_level == MailingList.ACCESS_LEVEL_STAFF:
        staff_addresses = ml._get_staff_members()
        bounce_back_email_template = None
        if sender not in staff_addresses:
            logger.info(
                "Sending mailing list bounce back email to %s for mailing list %s that is restricted to Staff, because"
                " the sender is not a staff member",
                sender,
                recipient
            )
            bounce_back_email_template = get_template('mailgun/email/bounce_back_non_member.html')

        if bounce_back_email_template:
            content = bounce_back_email_template.render(Context({
                'sender': sender,
                'recipient': recipient,
                'subject': subject,
                'message_body': message_body
            }))
            subject = "Insufficient acess to send  mail to this list"
            ml.send_mail(sender, subject, html=content)

    return JsonResponse({'success': True})

