from django.conf.urls import patterns, include, url


urlpatterns = patterns(
    '',
    url(r'^lti_emailer/lti_auth_error/', 'lti_emailer.views.lti_auth_error', name='lti_auth_error'),
    url(r'^lti_emailer/tool_config$', 'lti_emailer.views.tool_config', name='tool_config'),
    url(r'^lti_emailer/lti_launch$', 'lti_emailer.views.lti_launch', name='lti_launch'),
    url(r'^lti_emailer/mailing_list/', include('mailing_list.urls', namespace='mailing_list')),
)
