import json
import logging
import re

from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.utils.decorators import available_attrs
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from flanker.addresslib import address

from icommons_common.models import CourseInstance
from lti_emailer.canvas_api_client import get_name_for_email
from mailgun.decorators import authenticate
from mailgun.exceptions import HttpResponseException
from mailgun.listserv_client import MailgunClient as ListservClient
from mailing_list.models import MailingList, SuperSender, CourseSettings


logger = logging.getLogger(__name__)

listserv_client = ListservClient()


def handle_exceptions():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def inner(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except HttpResponseException as e:
                # sometimes we need to return an error response from deep down
                # the call stack.
                logger.exception(
                    u'HttpResponseException thrown by route handler, returning '
                    u'its encapsulated response %s.  POST data: %s',
                    e.response, json.dumps(request.POST, sort_keys=True))
                return e.response
            except:
                logger.exception(
                    u'Unhandled exception; aborting. POST data:\n%s\n',
                    json.dumps(request.POST, sort_keys=True))
                # tell Mailgun we're unhappy with message and to retry later
                return JsonResponse({'success': False}, status=500)
        return inner
    return decorator


@csrf_exempt
@authenticate()
@require_http_methods(['POST'])
@handle_exceptions()
def handle_mailing_list_email_route(request):
    '''
    Handles the Mailgun route action when email is sent to a Mailgun mailing list.
    :param request:
    :return JsonResponse:
    '''
    logger.debug(u'Full mailgun post: %s', request.POST)

    from_ = address.parse(request.POST.get('from'))
    message_id = request.POST.get('Message-Id')
    recipients = set(address.parse_list(request.POST.get('recipient')))
    sender = address.parse(request.POST.get('sender'))
    subject = request.POST.get('subject')

    logger.info(u'Handling Mailgun mailing list email from %s (sender %s) to '
                u'%s, subject %s, message id %s',
                from_, sender, recipients, subject, message_id)

    # short circuit if we detect a bounce loop
    sender_address = sender.address.lower() if sender else ''
    from_address = from_.address.lower() if from_ else ''
    if settings.NO_REPLY_ADDRESS.lower() in (sender_address, from_address):
        logger.error(u'Caught a bounce loop, dropping it. POST data:\n%s\n',
                     json.dumps(request.POST))
        return JsonResponse({'success': True})

    for recipient in recipients:
        # shortcut if we've already handled this message for this recipient
        if message_id:
            cache_key = (
                settings.CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT
                    % (message_id, recipient))
            if cache.get(cache_key):
                logger.warning(u'Message-Id %s was posted to the route handler '
                               u"for %s, but we've already handled that.  "
                               u'Skipping.', recipient, message_id)
                continue
        _handle_recipient(request, recipient)

    return JsonResponse({'success': True})


def _handle_recipient(request, recipient):
    '''
    The logic behind whether an email will be forwarded to list members or
    trigger a bounce email can be complicated.  A (hopefully simpler to follow)
    matrix can be found on the wiki:
        https://confluence.huit.harvard.edu/display/TLT/LTI+Emailer
    '''
    attachments, inlines = _get_attachments_inlines(request)
    body_html = request.POST.get('body-html', '')
    body_plain = request.POST.get('body-plain', '')
    cc_list = address.parse_list(request.POST.get('Cc'))
    parsed_from = address.parse(request.POST.get('from'))
    message_id = request.POST.get('Message-Id')
    sender = request.POST.get('sender')
    subject = request.POST.get('subject')
    to_list = address.parse_list(request.POST.get('To'))

    logger.debug(u'Handling recipient %s, from %s, subject %s, message id %s',
                 recipient, sender, subject, message_id)

    # short circuit if the mailing list doesn't exist
    try:
        ml = MailingList.objects.get_or_create_or_delete_mailing_list_by_address(
                 recipient.address)
    except MailingList.DoesNotExist:
        logger.info(
            u'Sending mailing list bounce back email to %s for mailing list %s '
            u'because the mailing list does not exist', sender, recipient)
        _send_bounce('mailgun/email/bounce_back_does_not_exist.html',
                     sender, recipient.full_spec(), subject,
                     body_plain or body_html, message_id)
        return

    # try to determine the course instance, and from there the school
    school_id = None
    ci = CourseInstance.objects.get_primary_course_by_canvas_course_id(ml.canvas_course_id)
    if ci:
        school_id = ci.course.school_id
    else:
        logger.warning(
            u'Could not determine the primary course instance for Canvas '
            u'course id %s, so we cannot prepend a short title to the '
            u'email subject, or check the super senders.', ml.canvas_course_id)

    member_addresses = set([m['address'].lower() for m in ml.members])

    # conditionally include staff addresses in the members list. If always_mail_staff is true
    # all staff will receive the email
    teaching_staff_addresses = ml.teaching_staff_addresses

    # if the course settings object does not exist create it, this equates to True
    print('ml.course_settings: {}'.format(ml.course_settings))
    if ml.course_settings is None:
        # we need to call get or create here as there might already be a setting for the
        # course in question that has not been applied to this list yet
        course_settings, created = CourseSettings.objects.get_or_create(canvas_course_id=ml.canvas_course_id)
        ml.course_settings = course_settings
        ml.save()

    if ml.course_settings and ml.course_settings.always_mail_staff:
        member_addresses = member_addresses.union(teaching_staff_addresses)

    # create a list of staff plus members to use to check permissions against
    # so all staff can email all lists
    staff_plus_members = teaching_staff_addresses.union(member_addresses)

    # if we can, grab the list of super senders
    super_senders = set()
    if school_id:
        # use iexact here to be able to match on COLGSAS or colgsas
        query = SuperSender.objects.filter(school_id__iexact=school_id)

        # lowercase all addresses in the supersenders list
        super_senders = {addr.lower() for addr
                             in query.values_list('email', flat=True)}

    # if we want to check email addresses against the sender, we need to parse
    # out the address from the display name.
    parsed_sender = address.parse(sender)
    sender_address = parsed_sender.address.lower()

    # any validation that fails will set the bounce template
    bounce_back_email_template = None

    # if not a super sender, check list membership and permissions
    if sender_address not in super_senders:
        if ml.access_level == MailingList.ACCESS_LEVEL_EVERYONE:
            pass
        elif sender_address not in staff_plus_members:
            # NOTE: list access is minimally ACCESS_LEVEL_MEMBERS at this point,
            #       so we want to let them know the email they sent from isn't
            #       a member of the list.
            logger.info(
                u'Sending mailing list bounce back email to %s for mailing list %s '
                u'because the sender was not a member', sender, recipient)
            bounce_back_email_template = 'mailgun/email/bounce_back_not_subscribed.html'
        elif ml.access_level == MailingList.ACCESS_LEVEL_READONLY:
            logger.info(
                u'Sending mailing list bounce back email to %s for mailing list %s '
                u'because the list is readonly', sender, recipient)
            bounce_back_email_template = 'mailgun/email/bounce_back_readonly_list.html'
        elif ml.access_level == MailingList.ACCESS_LEVEL_STAFF and sender_address not in teaching_staff_addresses:
            logger.info(
                u'Sending mailing list bounce back email to %s for mailing list %s '
                u'because the sender was not a staff member', sender, recipient)
            bounce_back_email_template = 'mailgun/email/bounce_back_access_denied.html'

    # bounce and return if they don't have the correct permissions
    if bounce_back_email_template:
        _send_bounce(bounce_back_email_template, sender, recipient.full_spec(),
                     subject, body_plain or body_html, message_id)
        return

    # finally, we can send the email to the list
    member_addresses = list(member_addresses)
    logger.debug(u'Full list of recipients: %s', member_addresses)

    # if we found the course instance, insert [SHORT TITLE] into the subject
    if ci and ci.short_title:
        title_prefix = '[{}]'.format(ci.short_title)
        if title_prefix not in subject:
            subject = title_prefix + ' ' + subject

    # we want to add 'via Canvas' to the sender's name.  do our best to figure
    # it out, then add 'via Canvas' as long as we could.
    logger.debug(u'Original sender: %s, original from: %s', sender, parsed_from)
    sender_display_name = _get_sender_display_name(parsed_sender, parsed_from, ml)
    if sender_display_name:
        sender_display_name += ' via Canvas'
    logger.debug(u'Final sender name: %s, sender address: %s',
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
    original_to_list = [a.full_spec() for a in to_list]
    original_cc_list = [a.full_spec() for a in cc_list]

    # and send it off
    logger.debug(
        u'Mailgun router handler sending email to %s from %s, subject %s',
        member_addresses, parsed_sender.full_spec(), subject)
    try:
        ml.send_mail(
            sender_display_name, sender_address,
            member_addresses, subject, text=body_plain, html=body_html,
            original_to_address=original_to_list, original_cc_address=original_cc_list,
            attachments=attachments, inlines=inlines, message_id=message_id
        )
    except RuntimeError:
        logger.exception(
            u'Error attempting to send message from %s to %s, originally '
            u'sent to list %s, with subject %s', parsed_sender.full_spec(),
            member_addresses, ml.address, subject)
        raise

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
    attachment_name_to_cid = {v: k.strip('<>') for k, v in content_id_map.iteritems()}
    logger.debug(u'Attachment name to cid: %s', attachment_name_to_cid)

    for n in xrange(1, attachment_count + 1):
        attachment_name = 'attachment-{}'.format(n)
        try:
            file_ = request.FILES[attachment_name]
        except KeyError:
            logger.exception(u'Mailgun POST claimed to have %s attachments, '
                             u'but %s is missing',
                             attachment_count, attachment_name)
            raise HttpResponseException(JsonResponse(
                      {
                          'message': 'Attachment {} missing from POST'.format(
                                         attachment_name),
                          'success': False,
                      },
                      status=400))
        if attachment_name in attachment_name_to_cid:
            file_.cid = attachment_name_to_cid[attachment_name]
            file_.name = file_.name.replace(' ', '_')
            inlines.append(file_)
        else:
            attachments.append(file_)

    return attachments, inlines


def _get_sender_display_name(parsed_sender, parsed_from, ml):
    sender_display_name = parsed_sender.display_name

    # first, try getting it from the "From" field
    if not sender_display_name:
        if parsed_sender.address == parsed_from.address:
            sender_display_name = parsed_from.display_name

    # fall back on looking up the enrollment, won't work for anyone not
    # enrolled in the course (ie. supersenders, globally sendable lists).
    if not sender_display_name:
        name = get_name_for_email(ml.canvas_course_id, parsed_sender.address)
        if name:
            sender_display_name = name
            logger.debug(u'Looked up display name for sender: %s, found: %s',
                         parsed_sender.address, sender_display_name)

    return sender_display_name


def _send_bounce(template_path, sender, recipient, subject, body, message_id):
    # send errors from a no-reply address so we don't get into bounceback loops
    no_reply_address = settings.NO_REPLY_ADDRESS

    template = get_template(template_path)
    content = template.render(Context({
        'sender': sender,
        'recipient': recipient,
        'subject': subject,
        'message_body': body,
    }))
    listserv_client.send_mail(no_reply_address, no_reply_address, sender,
                              subject='Undeliverable mail', html=content,
                              message_id=message_id)
