from django.conf.urls import url

from mailgun import api


urlpatterns = [
    url(r'^handle_mailing_list_email_route/', api.handle_mailing_list_email_route, name='handle_mailing_list_email_route'),
]
