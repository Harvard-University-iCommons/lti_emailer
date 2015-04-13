from datetime import datetime

from django.conf import settings
from django.db import models


class MailingList(models.Model):
    canvas_course_id = models.IntegerField()
    section_id = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=False)
    created_by = models.CharField(max_length=32)
    modified_by = models.CharField(max_length=32)
    date_created = models.DateTimeField(blank=True, default=datetime.utcnow)
    date_modified = models.DateTimeField(blank=True, default=datetime.utcnow)
    subscriptions_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ml_mailing_list'
        unique_together = ('canvas_course_id', 'section_id')

    def __unicode__(self):
        return u'canvas_course_id: {}, section_id: {}, active: {}'.format(
            self.canvas_course_id,
            self.section_id,
            self.active
        )

    @property
    def address(self):
        return "canvas-%s@%s" % (self.canvas_course_id, settings.LISTSERV_DOMAIN)


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
