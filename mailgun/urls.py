from django.conf.urls import url

from mailgun import views, route_handlers


urlpatterns = [
    url(r'^handle_mailing_list_email_route/', route_handlers.handle_mailing_list_email_route, name='handle_mailing_list_email_route'),
    url(r'^auth_error/', views.auth_error, name='auth_error'),
    url(r'^log_post_data/', views.log_post_data, name='log_post_data'),
]
