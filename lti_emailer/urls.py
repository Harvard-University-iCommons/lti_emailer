from django.conf.urls import patterns, include, url


urlpatterns = patterns(
    '',
    url(r'^tool_config$', 'lti_emailer.views.tool_config', name='tool_config'),
    url(r'^lti_launch$', 'lti_emailer.views.lti_launch', name='lti_launch'),
    url(r'^mailing_list/', include('mailing_list.urls', namespace='mailing_list')),
)
