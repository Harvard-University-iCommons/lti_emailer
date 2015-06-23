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
# @authenticate()
@require_http_methods(['POST'])
def handle_mailing_list_email_route(request):
    """
    Handles the Mailgun route action when email is sent to a Mailgun mailing list.
    1. Verify that recipient address is a course mailing list
    2. If access level of mailing list is 'members' and sender is not a member, send email response notifying the list
       did not receive the sender's email

    :param request:
    :return:
    """
    sender = request.POST.get('sender')
    recipient = request.POST.get('recipient')
    logger.info("Handling Mailgun mailing list email from %s to %s", sender, recipient)
    try:
        ml = MailingList.objects.get_mailing_list_by_address(recipient)
    except MailingList.DoesNotExist:
        message = "Could not find MailingList for email address %s" % recipient
        logger.error(message)
        return JsonResponse({'error': message}, status=406)  # Return status 406 so Mailgun does not retry

    member_addresses = [m['address'] for m in ml.members]
    if ml.access_level == MailingList.ACCESS_LEVEL_MEMBERS and sender not in member_addresses:
        logger.info("Sending mailing list bounce back email to %s for mailing list %s", sender, recipient)
        email_template = get_template('mailgun/non_member_bounce_back.html')
        content = email_template.render(Context({'mailing_list_address': recipient}))
        subject = "Undeliverable mail sent to %s" % recipient
        ml.send_mail(sender, subject, html=content)

    return JsonResponse({'success': True})
