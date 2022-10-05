import sys
import json
import logging
import re
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from flanker.addresslib import address as addresslib_address
from icommons_common.models import CourseInstance

from lti_emailer.canvas_api_client import (get_alternate_emails_for_user_email,
                                           get_name_for_email)
from mailgun.decorators import authenticate
from mailgun.exceptions import HttpResponseException
from mailgun.listserv_client import MailgunClient as ListservClient
from mailing_list.models import CourseSettings, MailingList, SuperSender

logger = logging.getLogger(__name__)

listserv_client = ListservClient()


def handle_exceptions():
    def decorator(view_func):
        @wraps(view_func)
        def inner(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except HttpResponseException as e:
                # sometimes we need to return an error response from deep down
                # the call stack.
                logger.exception(
                    'HttpResponseException thrown by route handler, returning '
                    'its encapsulated response %s.  POST data: %s',
                    e.response, json.dumps(request.POST, sort_keys=True))
                return e.response
            except:
                logger.exception(
                    'Unhandled exception; aborting. POST data:\n%s\n',
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
    logger.debug('Full mailgun post', extra=request.POST)
    logger.debug('request.files keys', extra={'keys': request.FILES.keys()})

    from_ = addresslib_address.parse(request.POST.get('from'))
    message_id = request.POST.get('Message-Id')
    recipients = set(addresslib_address.parse_list(request.POST.get('recipient')))
    sender = addresslib_address.parse(_remove_batv_prefix(request.POST.get('sender')))
    subject = request.POST.get('subject')
    user_alt_email_cache = CommChannelCache()

    logger.info('Handling Mailgun mailing list email from %s (sender %s) to '
                '%s, subject %s, message id %s',
                from_, sender, recipients, subject, message_id)

    # short circuit if we detect a bounce loop
    sender_address = sender.address.lower() if sender else ''
    from_address = from_.address.lower() if from_ else ''
    if settings.NO_REPLY_ADDRESS.lower() in (sender_address, from_address):
        logger.error('Caught a bounce loop, dropping it. POST data:\n%s\n',
                     json.dumps(request.POST))
        return JsonResponse({'success': True})

    for recipient in recipients:
        # shortcut if we've already handled this message for this recipient
        if message_id:
            cache_key = (
                settings.CACHE_KEY_MESSAGE_HANDLED_BY_MESSAGE_ID_AND_RECIPIENT
                    % (message_id, recipient))
            if cache.get(cache_key):
                logger.warning('Message-Id %s was posted to the route handler '
                               "for %s, but we've already handled that.  "
                               'Skipping.', recipient, message_id)
                continue
        _handle_recipient(request, recipient, user_alt_email_cache)

    return JsonResponse({'success': True})


def _handle_recipient(request, recipient, user_alt_email_cache):
    '''
    The logic behind whether an email will be forwarded to list members or
    trigger a bounce email can be complicated.  A (hopefully simpler to follow)
    matrix can be found on the wiki:
        https://confluence.huit.harvard.edu/display/TLT/LTI+Emailer
    '''
    body_html = request.POST.get('body-html', '')
    body_plain = request.POST.get('body-plain', '')
    cc_list = addresslib_address.parse_list(request.POST.get('Cc'))
    parsed_from = addresslib_address.parse(request.POST.get('from'))
    message_id = request.POST.get('Message-Id')
    sender = request.POST.get('sender')
    subject = request.POST.get('subject')
    to_list = addresslib_address.parse_list(request.POST.get('To'))

    attachments, inlines, eml_attachments, attachments_size = _get_attachments_inlines(
        request,
        sender,
        recipient,
        subject,
        body_plain,
        body_html,
        message_id
    )

    logger.debug('Handling recipient %s, from %s, subject %s, message id %s',
                 recipient, sender, subject, message_id)
    logger.info(f'attachments: {attachments}, inlines: {inlines}, eml_attachments: {eml_attachments}'
                f'attachments_total_size: {attachments_size} byte(s), from: {sender}, '
                f'message id: {message_id}')

    sender = _remove_batv_prefix(sender)

    # Send sender bounce email if attachments are greater than 25MB.
    # Mailgun's individual email size limit
    if attachments_size > 2.5e+7:
        logger.info(f'Sending mailing list bounce back email to {sender} '
                    f'for mailing list {recipient} because the email message exceeds '
                    f'the per-message size limit (including attachments) of 25MB')

        _send_bounce('mailgun/email/bounce_back_size_limit_exceeded.html',
                     sender, recipient.full_spec(), subject,
                     body_plain or body_html, message_id)
        return None

    # short circuit if the mailing list doesn't exist
    try:
        ml = MailingList.objects.get_or_create_or_delete_mailing_list_by_address(
                 recipient.address)
    except MailingList.DoesNotExist:
        logger.info(
            'Sending mailing list bounce back email to %s for mailing list %s '
            'because the mailing list does not exist', sender, recipient)
        _send_bounce('mailgun/email/bounce_back_does_not_exist.html',
                     sender, recipient.full_spec(), subject,
                     body_plain or body_html, message_id)
        return

    logger.debug('Got the MailingList object: {}'.format(ml))

    # try to determine the course instance, and from there the school
    school_id = None
    ci = CourseInstance.objects.get_primary_course_by_canvas_course_id(ml.canvas_course_id)
    if ci:
        school_id = ci.course.school_id
    else:
        logger.warning(
            'Could not determine the primary course instance for Canvas '
            'course id %s, so we cannot prepend a short title to the '
            'email subject, or check the super senders.', ml.canvas_course_id)

    member_addresses = set([m['address'].lower() for m in ml.members])
    logger.debug('Got member_addresses: %d', len(member_addresses))

    # conditionally include staff addresses in the members list. If
    # always_mail_staff is true all staff will receive the email
    teaching_staff_addresses = ml.teaching_staff_addresses
    logger.debug('Got teaching_staff_addresses: %d', len(teaching_staff_addresses))

    # if the course settings object does not exist create it to initialize the
    # defaults
    if ml.course_settings is None:
        # we need to call get or create here as there might already be a setting
        # for the course in question that has not been applied to this list yet
        course_settings, created = CourseSettings.objects.get_or_create(
            canvas_course_id=ml.canvas_course_id)
        ml.course_settings = course_settings
        ml.save()

    # for non-full-course mailing lists, only include teachers from other
    # sections if the course settings say to do so
    if ml.section_id is not None and ml.course_settings.always_mail_staff:
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
    parsed_sender = addresslib_address.parse(sender)
    sender_address = parsed_sender.address.lower()
    from_address = parsed_from.address.lower() if parsed_from else None

    # email to use as reply-to / sender; defaults to sender address, but if the
    # from address is the actual list member and the sender address is an active
    # communication channel in Canvas for said member we will use the from
    # address instead (see logic below)
    parsed_reply_to = None

    # any validation that fails will set the bounce template
    bounce_back_email_template = None

    # is sender or from_address a supersender?
    if from_address != sender_address and from_address in super_senders:
        alt_emails = user_alt_email_cache.get_for(from_address)
        if sender_address in alt_emails:
            parsed_reply_to = parsed_from
    elif sender_address in super_senders:
        parsed_reply_to = parsed_sender
    is_super_sender = bool(parsed_reply_to)

    # is the mailing list open to everyone?
    if not parsed_reply_to \
            and ml.access_level == MailingList.ACCESS_LEVEL_EVERYONE:
        parsed_reply_to = parsed_sender
        if from_address != sender_address \
                and from_address in staff_plus_members:
            alt_emails = user_alt_email_cache.get_for(from_address)
            if sender_address in alt_emails:
                parsed_reply_to = parsed_from

    if not parsed_reply_to:
        if ml.access_level == MailingList.ACCESS_LEVEL_STAFF:
            if from_address != sender_address \
                    and from_address in teaching_staff_addresses:
                # check if email is being sent on behalf of a list member by an
                # alternate email account
                alt_emails = user_alt_email_cache.get_for(from_address)
                if sender_address in alt_emails:
                    parsed_reply_to = parsed_from
                else:
                    # the from address matches a teaching staff list member, but
                    # the sender address is not a valid communication channel
                    # for that member in Canvas
                    # * note that alternate emails are not cached by default, so
                    # changes to a user's alternate emails in Canvas should be
                    # recognized immediately by this handler logic
                    logger.info(
                        'Sending mailing list bounce back email to sender for '
                        'mailing list %s because the sender address %s is not '
                        'one of the active email communication channels for '
                        'the list member matching the from address %s',
                        recipient, sender_address, from_address)
                    bounce_back_email_template = 'mailgun/email/bounce_back_no_comm_channel_match.html'
            elif sender_address in teaching_staff_addresses:
                parsed_reply_to = parsed_sender
            else:
                logger.info(
                    'Sending mailing list bounce back email to sender for '
                    'mailing list %s because neither the sender address %s '
                    'nor the from address %s was a staff member',
                    recipient, sender_address, from_address)
                bounce_back_email_template = 'mailgun/email/bounce_back_access_denied.html'

    if not parsed_reply_to and not bounce_back_email_template:
        # is sender or from_ a member of the list?
        if from_address != sender_address \
                and from_address in staff_plus_members:
            # check if email is being sent on behalf of a list member by an
            # alternate email account
            alt_emails = user_alt_email_cache.get_for(from_address)
            if sender_address in alt_emails:
                parsed_reply_to = parsed_from
            else:
                # the from address matches a list member, but the sender address
                # is not a valid communication channel for that member in Canvas
                # * note that alternate emails are not cached by default, so
                # changes to a user's alternate emails in Canvas should be
                # recognized immediately by this handler logic
                logger.info(
                    'Sending mailing list bounce back email to sender for '
                    'mailing list %s because the sender address %s is not one '
                    'of the active email communication channels for the list '
                    'member matching the from address %s',
                    recipient, sender_address, from_address)
                bounce_back_email_template = 'mailgun/email/bounce_back_no_comm_channel_match.html'
        elif sender_address in staff_plus_members:
            parsed_reply_to = parsed_sender
        else:
            # neither of the possible sender addresses matches a list member
            logger.info(
                'Sending mailing list bounce back email to sender for '
                'mailing list %s because neither the sender address %s '
                'nor the from address %s was a member',
                recipient, sender_address, from_address)
            bounce_back_email_template = 'mailgun/email/bounce_back_not_subscribed.html'

    if not is_super_sender and not bounce_back_email_template:
        if ml.access_level == MailingList.ACCESS_LEVEL_READONLY:
            logger.info(
                'Sending mailing list bounce back email to sender '
                'address %s (from address %s) for mailing list %s because '
                'the list is readonly', sender_address, from_address,
                recipient)
            bounce_back_email_template = 'mailgun/email/bounce_back_readonly_list.html'

    # bounce and return if they don't have the correct permissions
    if bounce_back_email_template:
        _send_bounce(bounce_back_email_template, sender, recipient.full_spec(),
                     subject, body_plain or body_html, message_id)
        return

    # always send the email to the sender. Add 'parsed_reply_to to the
    # member_addresses set(tlt-2960)
    logger.debug('Adding parsed_reply_to (sender) address to the final '
                 'recipient list:%s.', parsed_reply_to.address.lower())
    member_addresses.add(parsed_reply_to.address.lower())

    # finally, we can send the email to the list
    member_addresses = list(member_addresses)
    logger.debug('Full list of recipients: %s', member_addresses)

    # if we found the course instance, insert [SHORT TITLE] into the subject
    if ci and ci.short_title:
        title_prefix = '[{}]'.format(ci.short_title)
        if title_prefix not in subject:
            subject = title_prefix + ' ' + subject

    # we want to add 'via Canvas' to the sender's name.  do our best to figure
    # it out, then add 'via Canvas' as long as we could.
    logger.debug(
        'Original sender: %s, original from: %s, using %s as reply-to and '
        'sender address', parsed_sender, parsed_from, parsed_reply_to)
    reply_to_display_name = _get_sender_display_name(
        parsed_reply_to, parsed_from, ml)
    if reply_to_display_name:
        reply_to_display_name += ' via Canvas'
    logger.debug('Final sender name: %s, sender address: %s',
                 reply_to_display_name, parsed_reply_to.address.lower())

    # make sure inline images actually show up inline, since fscking
    # mailgun won't let us specify the cid on post.  see their docs at
    # https://documentation.mailgun.com/en/latest/user_manual.html#sending-via-api
    # where they explain that they use the inlined file's name attribute
    # as the content-id.
    if inlines:
        for f in inlines:
            logger.debug('Replacing "%s" with "%s" in body', f.cid, f.name)
            body_plain = re.sub(f.cid, f.name, body_plain)
            body_html = re.sub(f.cid, f.name, body_html)

    # convert the original to/cc fields back to strings so we can send
    # them along through the listserv
    original_to_list = [a.full_spec() for a in to_list]
    original_cc_list = [a.full_spec() for a in cc_list]

    # and send it off
    logger.debug(
        'Mailgun router handler sending email to %s from %s, subject %s',
        member_addresses, parsed_reply_to.full_spec(), subject)
    try:
        ml.send_mail(
            reply_to_display_name, parsed_reply_to.address.lower(),
            member_addresses, subject, text=body_plain, html=body_html,
            original_to_address=original_to_list, original_cc_address=original_cc_list,
            attachments=attachments, inlines=inlines, eml_attachments=eml_attachments,  
            message_id=message_id
        )
    except RuntimeError:
        logger.exception(
            'Error attempting to send message from %s to %s, originally '
            'sent to list %s, with subject %s', parsed_reply_to.full_spec(),
            member_addresses, ml.address, subject)
        raise

    return JsonResponse({'success': True})


def _get_attachments_inlines(request, sender, recipient, subject, body_plain, body_html, message_id):
    attachments = []
    inlines = []
    eml_attachments = {}
    attachments_size = 0

    try:
        attachment_count = int(request.POST.get('attachment-count', 0))
    except RuntimeError:
        logger.exception(
            'Unable to determine if there were attachments to this email')
        attachment_count = 0

    try:
        content_id_map = json.loads(request.POST.get('content-id-map', '{}'))
    except RuntimeError:
        logger.exception('Unable to find content-id map in this email, '
                         'forwarding all files as attachments.')
        content_id_map = {}
    attachment_name_to_cid = {v: k.strip('<>') for k, v in content_id_map.items()}
    logger.info('Attachment name to cid: %s', attachment_name_to_cid)

    for n in range(1, attachment_count + 1):
        attachment_name = 'attachment-{}'.format(n)
        if request.POST.get(attachment_name):
            eml_attachments[attachment_name] = (request.POST.get(attachment_name))
            attachments_size += sys.getsizeof(eml_attachments[attachment_name])
            continue
        elif request.FILES.get(attachment_name):
            file_ = request.FILES[attachment_name]
        else:
            log_attachment_error_warn_user(attachment_count, attachment_name, sender, recipient, subject,
                                           body_plain, body_html, message_id, content_id_map)

        if attachment_name in attachment_name_to_cid:
            file_.cid = attachment_name_to_cid[attachment_name]
            file_.name = file_.name.replace(' ', '_')
            inlines.append(file_)
        else:
            attachments.append(file_)

        attachments_size += file_

    return attachments, inlines, eml_attachments, attachments_size


def log_attachment_error_warn_user(attachment_count, attachment_name, sender, recipient, subject,
                                   body_plain, body_html, message_id, content_id_map):
    logger.exception(
        f'Mailgun POST claimed to have {attachment_count} attachments, '
        f'but {attachment_name} is missing'
    )

    logger.info(f'Sent bounce back email to {sender} for mailing list {recipient} '
                f'because Mailgun POST claimed to have {attachment_count} '
                f'attachments but {attachment_name} is missing',
                extra={
                    'sender': sender,
                    'recipient': recipient,
                    'content_id_map': content_id_map,
                    'attachment_count': attachment_count,
                    'attachment_name': attachment_name
                }
                )

    _send_bounce('mailgun/email/bounce_back_attachments_missing.html',
                 sender, recipient.full_spec(), subject,
                 body_plain or body_html, message_id)

    raise HttpResponseException(JsonResponse(
        {
            'message': 'Attachment {} missing from POST'.format(
                attachment_name),
            'success': False,
        },
        status=400))


def _remove_batv_prefix(sender_address):
    # Strip BATV prefix from the envelope-sender address if present
    batv_pattern = '^\w+=+[^=]+=+(.+)'
    try:
        batv_address = re.match(batv_pattern, sender_address)
        if batv_address:
            logger.warning('sender address ({}) has BATV prefix, removing: {}'.format(batv_address.group(0), batv_address.group(1)))
            return batv_address.group(1)
    except Exception:
        logger.exception('error while removing BATV prefix ({}) from {}/{}'.format(batv_pattern, sender_address, type(sender_address)))

    # otherwise just return the original address
    return sender_address


class CommChannelCache(object):
    """
    Cache layer for Canvas calls to get alternate communication channels.
    This could/should be replaced by caching in an appropriate object tied
    to the mailgun event.

    This really only useful if the logic in the access checking section of
    _handle_recipient() has to request alternate emails more than
    once for the same `from` address, e.g. when multiple mailing lists are
    handled in a single handle_mailing_list_email_route() command invocation,
    or if the logic eventually has pathways that could result in multiple checks
    for the same recipient.
    """

    def __init__(self):
        self._user_map = {}

    def get_for(self, email_address):
        """
        returns and caches a list of valid alternate emails for `email_address`.
        Find user via search in Canvas, and determine if user
        """
        alt_emails = self._user_map.get(email_address)
        if alt_emails is None:
            alt_emails = get_alternate_emails_for_user_email(email_address)
            self._user_map[email_address] = alt_emails
            logger.debug('Caching valid alternate emails for user {}: '
                         '{}'.format(email_address, alt_emails))
        return alt_emails


def _get_sender_display_name(parsed_reply_to, parsed_from, ml):
    # Use the user's preferred display name if provided
    sender_display_name = parsed_reply_to.display_name
    reply_to_address = parsed_reply_to.address.lower()

    # get it from the 'from' address if we don't already have it (only if the
    # from address matches the sender)
    if not sender_display_name and \
            reply_to_address == parsed_from.address.lower():
        sender_display_name = parsed_from.display_name

    # if we still don't have a display name, fall back on looking up the
    # enrollment; note even this won't work for anyone not enrolled in the
    # course (ie. supersenders, globally sendable lists).
    if not sender_display_name:
        sender_display_name = get_name_for_email(ml.canvas_course_id,
                                                 reply_to_address)
        if sender_display_name:
            logger.debug(
                'Looked up enrollment information to find display name for '
                'sender %s, found: %s', reply_to_address, sender_display_name)

    return sender_display_name


def _send_bounce(template_path, sender, recipient, subject, body, message_id):
    # send errors from a no-reply address so we don't get into bounceback loops
    no_reply_address = settings.NO_REPLY_ADDRESS

    template = get_template(template_path)
    content = template.render({
        'sender': sender,
        'recipient': recipient,
        'subject': subject,
        'message_body': body,
    })
    listserv_client.send_mail(no_reply_address, no_reply_address, sender,
                              subject='Undeliverable mail', html=content,
                              message_id=message_id)
