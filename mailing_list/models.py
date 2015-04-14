import logging
import json

from datetime import datetime

from django.conf import settings
from django.db import models
from django.core.cache import cache

from canvas_sdk.methods import enrollments, sections
from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import Person

from .listserv_clients.mailgun import MailgunClient as ListservClient


SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


logger = logging.getLogger(__name__)


listserv_client = ListservClient()


class MailingListManager(models.Manager):
    def get_or_create_mailing_lists_for_canvas_course_id(self, canvas_course_id, **kwargs):
        cache_key = settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % canvas_course_id
        lists = cache.get(cache_key, {})
        if not lists:
            try:
                canvas_sections = get_all_list_data(SDK_CONTEXT, sections.list_course_sections, canvas_course_id)
            except CanvasAPIError:
                logger.exception("Failed to get canvas sections for canvas_course_id %s", canvas_course_id)
                raise

            mailing_lists_by_section_id = {ml.section_id: ml for ml in MailingList.objects.filter(canvas_course_id=canvas_course_id)}

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

                access_level = 'members'
                listserv_list = listserv_client.get_list(mailing_list)
                if not listserv_list:
                    listserv_client.create_list(mailing_list)
                else:
                    access_level = listserv_list['access_level']

                members_count = mailing_list.sync_listserv_membership()

                lists[section_id] = {
                    'id': mailing_list.id,
                    'name': s['name'],
                    'address': mailing_list.address,
                    'access_level': access_level,
                    'members_count': members_count,
                    'is_primary_section': s['sis_section_id'] is not None
                }

            cache.set(cache_key, lists)

        return lists.values()


class MailingList(models.Model):
    canvas_course_id = models.IntegerField()
    section_id = models.IntegerField()
    created_by = models.CharField(max_length=32)
    modified_by = models.CharField(max_length=32)
    date_created = models.DateTimeField(blank=True, default=datetime.utcnow)
    date_modified = models.DateTimeField(blank=True, default=datetime.utcnow)
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

    @property
    def address(self):
        return "canvas-%s-%s@%s" % (self.canvas_course_id, self.section_id, settings.LISTSERV_DOMAIN)

    def update_access_level(self, access_level):
        logger.debug("Updating access_level for listserv mailing list %s with %s", self.address, access_level)
        listserv_client.update_list(self, access_level)
        cache.delete(settings.CACHE_KEY_LISTS_BY_CANVAS_COURSE_ID % self.canvas_course_id)
        logger.debug("Finished updating listserv mailing list for canvas_course_id %s", self.canvas_course_id)

    def sync_listserv_membership(self):
        logger.debug("Synchronizing listserv membership for canvas course id %s", self.canvas_course_id)

        canvas_course_id = self.canvas_course_id
        unsubscribed = {x.email for x in self.unsubscribed_set.all()}

        try:
            canvas_enrollments = get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_courses, canvas_course_id)
        except CanvasAPIError:
            logger.exception("Failed to get canvas enrollments for canvas_course_id %s", canvas_course_id)
            raise

        univ_ids = []
        for enrollment in canvas_enrollments:
            try:
                univ_ids.append(enrollment['user']['sis_user_id'])
            except KeyError:
                logger.debug("Found canvas enrollment with missing sis_user_id %s", json.dumps(enrollment, indent=4))
        enrolled_emails = set([p.email_address for p in Person.objects.filter(univ_id__in=univ_ids)])

        mailing_list_emails = enrolled_emails - unsubscribed

        # Only add subscribers to the listserv if:
        # 1. The subscriber is on the whitelist
        # OR
        # 2. Settings tell us to ignore the whitelist
        if not hasattr(settings, 'IGNORE_WHITELIST'):
            mailing_list_emails = mailing_list_emails.intersection({x.email for x in EmailWhitelist.objects.all()})

        listserv_emails = {m['address'] for m in listserv_client.members(self)}

        members_to_add = mailing_list_emails - listserv_emails
        members_to_delete = listserv_emails - mailing_list_emails

        listserv_client.add_members(self, members_to_add)
        listserv_client.delete_members(self, members_to_delete)

        logger.debug("Finished synchronizing listserv membership for canvas_course_id %s", self.canvas_course_id)

        return len(listserv_emails) + len(members_to_add) - len(members_to_delete)


class Unsubscribed(models.Model):
    mailing_list = models.ForeignKey(MailingList)
    email = models.EmailField()
    created_by = models.CharField(max_length=32)
    date_created = models.DateTimeField(blank=True, default=datetime.utcnow)

    class Meta:
        db_table = 'ml_unsubscribed'
        unique_together = ('mailing_list', 'email')

    def __unicode__(self):
        return u'mailing_list_id: {}, email: {}'.format(
            self.mailing_list.id,
            self.email
        )


class EmailWhitelist(models.Model):
    email = models.EmailField()

    class Meta:
        db_table = 'ml_email_whitelist'

    def __unicode__(self):
        return u'email: {}'.format(
            self.email
        )
