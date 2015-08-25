from django.conf.urls import include, url

from lti_emailer import views


urlpatterns = [
    url(r'^lti_auth_error/', views.lti_auth_error, name='lti_auth_error'),
    url(r'^tool_config$', views.tool_config, name='tool_config'),
    url(r'^lti_launch$', views.lti_launch, name='lti_launch'),
    url(r'^mailing_list/', include('mailing_list.urls', namespace='mailing_list')),
    url(r'^mailgun/', include('mailgun.urls', namespace='mailgun')),
    url(r'^not_authorized/$', 'icommons_ui.views.not_authorized',
        name='not_authorized'),
    url(r'^interactions/', include('interactions.urls', namespace='interactions')),
]
