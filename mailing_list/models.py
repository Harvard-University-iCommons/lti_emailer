import logging
import json

from datetime import datetime

from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.utils import timezone

from icommons_common.models import (
    Person,
    CourseStaff,
)

from lti_emailer import canvas_api_client
from mailgun.listserv_client import MailgunClient as ListservClient


logger = logging.getLogger(__name__)


listserv_client = ListservClient()


class MailingListManager(models.Manager):
    """
    Custom Manager for working with MailingList models.
    """
    def _get_mailing_lists_by_section_id(self, canvas_course_id):
        return {ml.section_id: ml for ml in MailingList.objects.filter(canvas_course_id=canvas_course_id)}

    def get_mailing_list_by_address(self, address):
        try:
            (_, canvas_course_id, section_id) = address.split('@')[0].split('-')
        except (AttributeError, ValueError):
            logger.error("Failed to parse address in get_mailing_list_by_address %s", address)
            raise MailingList.DoesNotExist
        return MailingList.objects.get(canvas_course_id=canvas_course_id, section_id=section_id)

    def get_or_create_mailing_lists_for_canvas_course_id(self, canvas_course_id, **kwargs):
        """
        Gets the mailing list data for all sections related to the given canvas_course_id.
        Creates MailingList models and corresponding listserv mailing lists if a given section's
        mailing list does not yet exist. This will also sync the mailing list membership with the
        course enrollments when creating new mailing lists.

        :param canvas_course_id:
        :param kwargs:
        :return: List of mailing list dictionaries for the given canvas_course_id
        """
        cache_key = settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % canvas_course_id
        lists = cache.get(cache_key, {})
        if not lists:
            canvas_sections = canvas_api_client.get_sections(canvas_course_id)
            mailing_lists_by_section_id = self._get_mailing_lists_by_section_id(canvas_course_id)

            overrides = kwargs.get('defaults', {})
            for s in canvas_sections:
                section_id = s['id']
                mailing_list = mailing_lists_by_section_id.get(section_id)
                if not mailing_list:
                    create_kwargs = {
                        'canvas_course_id': canvas_course_id,
                        'section_id': section_id
                    }
                    create_kwargs.update(overrides)

                    mailing_list = MailingList(**create_kwargs)
                    mailing_list.save()

                listserv_list = listserv_client.get_list(mailing_list)
                if not listserv_list:
                    listserv_client.create_list(mailing_list)

                members_count = mailing_list.sync_listserv_membership()

                lists[section_id] = {
                    'id': mailing_list.id,
                    'canvas_course_id': mailing_list.canvas_course_id,
                    'section_id': mailing_list.section_id,
                    'name': s['name'],
                    'address': mailing_list.address,
                    'access_level': mailing_list.access_level,
                    'members_count': members_count,
                    'is_primary_section': s['sis_section_id'] is not None
                }

            cache.set(cache_key, lists)

        return lists.values()


class MailingList(models.Model):
    """
    This model tracks mailing lists created on a third-party listserv service.
    These mailing lists correspond to a given canvas_course_id:section_id combination.
    """
    ACCESS_LEVEL_MEMBERS = 'members'
    ACCESS_LEVEL_EVERYONE = 'everyone'
    ACCESS_LEVEL_READONLY = 'readonly'
    ACCESS_LEVEL_STAFF = 'staff'

    canvas_course_id = models.IntegerField()
    section_id = models.IntegerField()
    access_level = models.CharField(max_length=32, default='members')
    created_by = models.CharField(max_length=32)
    modified_by = models.CharField(max_length=32)
    date_created = models.DateTimeField(blank=True, default=timezone.now)
    date_modified = models.DateTimeField(blank=True, default=timezone.now)
    subscriptions_updated = models.DateTimeField(null=True, blank=True)

    objects = MailingListManager()

    class Meta:
        db_table = 'ml_mailing_list'
        unique_together = ('canvas_course_id', 'section_id')

    def __unicode__(self):
        return u'canvas_course_id: {}, section_id: {}'.format(
            self.canvas_course_id,
            self.section_id
        )

    def _get_unsubscribed_email_set(self):
        return {x.email for x in self.unsubscribed_set.all()}

    def _get_enrolled_persons(self):
        univ_ids = []
        canvas_enrollments = canvas_api_client.get_enrollments(self.canvas_course_id, self.section_id)
        for enrollment in canvas_enrollments:
            try:
                univ_ids.append(enrollment['user']['sis_user_id'])
            except KeyError:
                logger.debug(
                    "Found canvas enrollment with missing sis_user_id %s",
                    json.dumps(enrollment, indent=4))
        return Person.objects.filter(univ_id__in=univ_ids)

    def _get_enrolled_email_set(self):
        return {p.email_address for p in self._get_enrolled_persons()}

    def _get_whitelist_email_set(self):
        return {x.email for x in EmailWhitelist.objects.all()}

    def _get_listserv_email_set(self):
        return {m['address'] for m in listserv_client.members(self)}

    @property
    def address(self):
        return settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=self.canvas_course_id,
            section_id=self.section_id
        )

    @property
    def listserv_access_level(self):
        listserv_list = listserv_client.get_list(self)
        return listserv_list['access_level']

    @property
    def members(self):
        return listserv_client.members(self)

    @property
    def teaching_staff_addresses(self):
        teaching_staff_enrollments = canvas_api_client.get_teaching_staff_enrollments(self.canvas_course_id)
        univ_ids = []
        for enrollment in teaching_staff_enrollments:
            try:
                univ_ids.append(enrollment['user']['sis_user_id'])
            except KeyError:
                logger.debug(
                    "Found canvas staff enrollment with missing sis_user_id %s",
                    json.dumps(enrollment, indent=4)
                )
        people = Person.objects.filter(univ_id__in=univ_ids)
        addresses = [email for email in people.values_list('email_address', flat=True)]
        logger.debug("Returning teaching staff email list from MailingList.teaching_staff_email_set: %s" % addresses)
        return addresses

    def emails_by_user_id(self):
        return {p.univ_id: p.email_address for p in self._get_enrolled_persons()}

    def send_mail(self, sender_address, to_address, subject='', text='', html=''):
        logger.debug("   in send_mail: sender_address=%s, to_address=%s, mailing_list.address=%s "
                     % (sender_address, to_address, self.address))
        formatted_from_address = sender_address + '<'+self.address+'>'
        logger.debug("formatted_from_address=%s " % formatted_from_address)
        listserv_client.send_mail(sender_address, to_address,  self.address, subject, text, html)

    def sync_listserv_membership(self):
        """
        Synchronize the listserv mailing list membership with the course enrollments
        for the given canvas_course_id:section_id.

        :return: The members count for this mailing list.
        """
        logger.debug("Synchronizing listserv membership for canvas course id %s", self.canvas_course_id)

        # Clear Canvas API enrollment cache before syncing to make sure we have the latest data
        cache.delete(settings.CACHE_KEY_CANVAS_ENROLLMENTS_BY_CANVAS_SECTION_ID % self.section_id)

        unsubscribed_emails = self._get_unsubscribed_email_set()
        enrolled_emails = self._get_enrolled_email_set()
        mailing_list_emails = enrolled_emails - unsubscribed_emails

        # Only add subscribers to the listserv if:
        # 1. The subscriber is on the whitelist
        # OR
        # 2. Settings tell us to ignore the whitelist
        if not getattr(settings, 'IGNORE_WHITELIST', False):
            whitelist_emails = self._get_whitelist_email_set()
            mailing_list_emails = mailing_list_emails.intersection(whitelist_emails)

        listserv_emails = self._get_listserv_email_set()

        members_to_add = mailing_list_emails - listserv_emails
        members_to_delete = listserv_emails - mailing_list_emails

        listserv_client.add_members(self, members_to_add)
        listserv_client.delete_members(self, members_to_delete)

        # Update MailingList subscriptions_updated audit field
        self.subscriptions_updated = timezone.now()
        self.save()

        logger.debug("Finished synchronizing listserv membership for canvas_course_id %s", self.canvas_course_id)
        cache.delete(settings.CACHE_KEY_CANVAS_SECTIONS_BY_CANVAS_COURSE_ID % self.canvas_course_id)
        cache.delete(settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % self.canvas_course_id)

        # Return the listserv members count
        return len(listserv_emails) + len(members_to_add) - len(members_to_delete)


class Unsubscribed(models.Model):
    """
    This model is used to keep track of mailing list members who have unsubscribed from the list.
    """
    mailing_list = models.ForeignKey(MailingList)
    email = models.EmailField()
    created_by = models.CharField(max_length=32)
    date_created = models.DateTimeField(blank=True, default=timezone.now)

    class Meta:
        db_table = 'ml_unsubscribed'
        unique_together = ('mailing_list', 'email')

    def __unicode__(self):
        return u'mailing_list_id: {}, email: {}'.format(
            self.mailing_list.id,
            self.email
        )


class EmailWhitelist(models.Model):
    """
    This model is used in testing/qa environments to ensure we do not
    accidentally send email to real users.
    """
    email = models.EmailField()

    class Meta:
        db_table = 'ml_email_whitelist'

    def __unicode__(self):
        return u'email: {}'.format(
            self.email
        )
