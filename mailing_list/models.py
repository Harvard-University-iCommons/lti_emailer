import logging

from flanker import addresslib

from django.conf import settings
from django.db import models
from django.utils import timezone

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

            mailing_lists_by_section_id[section_id] = {
                'id': mailing_list.id,
                'canvas_course_id': mailing_list.canvas_course_id,
                'section_id': mailing_list.section_id,
                'name': s['name'],
                'address': mailing_list.address,
                'access_level': mailing_list.access_level,
                'members_count': len(mailing_list.members),
                'is_primary_section': s['sis_section_id'] is not None
            }

        return mailing_lists_by_section_id.values()


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

    objects = MailingListManager()

    class Meta:
        db_table = 'ml_mailing_list'
        unique_together = ('canvas_course_id', 'section_id')

    def __unicode__(self):
        return u'canvas_course_id: {}, section_id: {}'.format(
            self.canvas_course_id,
            self.section_id
        )

    def _get_enrolled_email_set(self):
        return {e['email'] for e in canvas_api_client.get_enrollments(self.canvas_course_id, self.section_id)}

    def _get_enrolled_teaching_staff_email_set(self):
        return {e['email'] for e in canvas_api_client.get_teaching_staff_enrollments(self.canvas_course_id)}

    def _get_whitelist_email_set(self):
        return {x.email for x in EmailWhitelist.objects.all()}

    @property
    def address(self):
        return settings.LISTSERV_ADDRESS_FORMAT.format(
            canvas_course_id=self.canvas_course_id,
            section_id=self.section_id
        )

    @property
    def members(self):
        mailing_list_emails = self._get_enrolled_email_set()
        if not getattr(settings, 'IGNORE_WHITELIST', False):
            mailing_list_emails = mailing_list_emails.intersection(self._get_whitelist_email_set())
        return [{'address': e} for e in mailing_list_emails]

    @property
    def teaching_staff_addresses(self):
        return self._get_enrolled_teaching_staff_email_set()

    def send_mail(self, sender_display_name, sender_address, to_address,
                  subject='', text='', html='', original_to_address=None,
                  original_cc_address=None, attachments=None, inlines=None):
        logger.debug("in send_mail: sender_address=%s, to_address=%s, "
                     "mailing_list.address=%s ",
                     sender_address, to_address, self.address)
        mailing_list_address = addresslib.address.parse(self.address)
        mailing_list_address.display_name = sender_display_name
        listserv_client.send_mail(
            mailing_list_address.full_spec(), sender_address, to_address,
            subject, text, html, original_to_address, original_cc_address,
            attachments, inlines
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
