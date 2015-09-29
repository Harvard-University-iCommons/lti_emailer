import logging

import re
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

    def _parse_address(self, address):
        """
        Try to parse out the canvas_course_id and section_id from the email address.
        :param address:
        :return (canvas_course_id, section_id):
        """
        try:
            # Try to match course/section address
            m = re.search(settings.LISTSERV_SECTION_ADDRESS_RE, address)
            if m:
                canvas_course_id = int(m.group('canvas_course_id'))
                section_id = int(m.group('section_id'))
            else:
                # Try to match course address
                m = re.search(settings.LISTSERV_COURSE_ADDRESS_RE, address)
                canvas_course_id = int(m.group('canvas_course_id'))
                # section needs to be None for this kind of address
                section_id = None
        except (IndexError, AttributeError):
            raise MailingList.DoesNotExist

        return canvas_course_id, section_id

    def get_or_create_or_delete_mailing_list_by_address(self, address):

        (canvas_course_id, section_id) = self._parse_address(address)
        if section_id:
            # if there is a section id, make sure that a section exists in canvas.
            canvas_section = canvas_api_client.get_section(canvas_course_id, section_id)
            if canvas_section:
                try:
                    mailing_list = MailingList.objects.get(canvas_course_id=canvas_course_id, section_id=section_id)
                except MailingList.DoesNotExist:
                    mailing_list = MailingList(canvas_course_id=canvas_course_id, section_id=section_id)
                    mailing_list.save()
            else:
                # Section with section_id no longer exists, so delete the associated mailing list
                MailingList.objects.get(canvas_course_id=canvas_course_id, section_id=section_id).delete()
                raise MailingList.DoesNotExist
        else:
            # if there is not a section_id, this is a class list, try to get it otherwise it will throw DoesNotExist
            # This address is created in the calling method.
            mailing_list = MailingList.objects.get(canvas_course_id=canvas_course_id, section_id__isnull=True)
            
        return mailing_list

    def get_or_create_or_delete_mailing_lists_for_canvas_course_id(self, canvas_course_id, **kwargs):
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

        # get a list of the primary sections
        primary_sections = [s['id'] for s in canvas_sections if s['sis_section_id'] is not None]

        overrides = kwargs.get('defaults', {})
        result = []

        # if there is more than one primary section
        # create a primary mailing list.
        course_list = None
        if len(primary_sections) > 1:
            try:
                course_list = mailing_lists_by_section_id.pop(None)
            except KeyError:
                course_list = None

            if not course_list:
                create_kwargs = {
                    'canvas_course_id': canvas_course_id,
                    'section_id': None
                }
                create_kwargs.update(overrides)
                course_list = MailingList(**create_kwargs)
                course_list.save()

        # if there is a course_list, append it to the result list so
        # it can be used by the template.
        if course_list:
            result.append({
                'id': course_list.id,
                'canvas_course_id': course_list.canvas_course_id,
                'section_id': course_list.section_id,
                'name': canvas_api_client.get_course(canvas_course_id)['course_code'],
                'address': course_list.address,
                'access_level': course_list.access_level,
                'members_count': len(course_list.members),
                'is_primary_section': True,
                'is_course_list': True,
            })

        for s in canvas_sections:
            section_id = s['id']
            try:
                mailing_list = mailing_lists_by_section_id.pop(section_id)
            except KeyError:
                mailing_list = None

            if not mailing_list:
                create_kwargs = {
                    'canvas_course_id': canvas_course_id,
                    'section_id': section_id
                }
                create_kwargs.update(overrides)
                mailing_list = MailingList(**create_kwargs)
                mailing_list.save()

            result.append({
                'id': mailing_list.id,
                'canvas_course_id': mailing_list.canvas_course_id,
                'section_id': mailing_list.section_id,
                'name': s['name'],
                'address': mailing_list.address,
                'access_level': mailing_list.access_level,
                'members_count': len(mailing_list.members),
                'is_primary_section': s['sis_section_id'] is not None
            })

        # Delete existing mailing lists who's section no longer exists
        for section_id, mailing_list in mailing_lists_by_section_id.iteritems():
            mailing_list.delete()

        return result


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
    section_id = models.IntegerField(null=True)
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

        """
        When we add enrollment emails to the mailing list, check if this is a whole course list
        by checking if the section_id is 0. If it is we want to add all the enrollments that exist
        in the course. If not, we build the mailing with the enrollments for the specified section.
        """
        return {
            e['email'].lower() for e in canvas_api_client.get_enrollments(self.canvas_course_id, self.section_id)
            if e['email'] is not None
        }

    def _get_enrolled_teaching_staff_email_set(self):
        return {
            e['email'].lower() for e in canvas_api_client.get_teaching_staff_enrollments(self.canvas_course_id)
            if e['email'] is not None
        }

    def _get_whitelist_email_set(self):
        return {x.email.lower() for x in EmailWhitelist.objects.all()}

    @property
    def address(self):
        if not self.section_id:
            return settings.LISTSERV_COURSE_ADDRESS_FORMAT.format(canvas_course_id=self.canvas_course_id)
        return settings.LISTSERV_SECTION_ADDRESS_FORMAT.format(
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
        logger.debug(u"in send_mail: sender_address=%s, to_address=%s, "
                     u"mailing_list.address=%s ",
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
