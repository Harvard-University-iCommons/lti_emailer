from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete

from .models import MailingList
from .listserv_clients.mailgun import MailgunClient as ListservClient
from .utils import sync_mailing_lists_with_listserv


@receiver(pre_save, sender=MailingList, dispatch_uid="mailing_list_pre_save")
def handle_mailing_list_pre_save(sender, instance, **kwargs):
    if instance.active:
        ListservClient().create_list(instance)
        sync_mailing_lists_with_listserv([instance])


@receiver(post_save, sender=MailingList, dispatch_uid="mailing_list_post_save")
def handle_mailing_list_post_save(sender, instance, created, **kwargs):
    if not instance.active and not created:
        ListservClient().delete_list(instance)


@receiver(post_delete, sender=MailingList, dispatch_uid="mailing_list_post_delete")
def handle_mailing_list_post_delete(sender, instance, **kwargs):
    if instance.active:
        ListservClient().delete_list(instance)


def _sync_mailing_lists_for_canvas_course_id(canvas_course_id):
    sync_mailing_lists_with_listserv(MailingList.objects.filter(canvas_course_id=canvas_course_id, active=True))
