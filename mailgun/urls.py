from django.urls import path, re_path

from mailgun import views, route_handlers


urlpatterns = [
    re_path(r'^handle_mailing_list_email_route/', route_handlers.handle_mailing_list_email_route, name='handle_mailing_list_email_route'),
    path('auth_error/', views.auth_error, name='auth_error'),
    re_path(r'^log_post_data/', views.log_post_data, name='log_post_data'),
]
