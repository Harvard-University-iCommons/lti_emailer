from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(r'^admin_index/(?P<resource_link_id>\w+)$', 'mailing_list.views.admin_index', name='admin_index'),
    url(r'^learner_index/(?P<resource_link_id>\w+)$', 'mailing_list.views.learner_index', name='learner_index'),
    url(r'^api/lists/(?P<resource_link_id>\w+)$', 'mailing_list.api.lists', name='api_lists'),
    url(r'^api/lists/(?P<mailing_list_id>\d+)/set_access_level/(?P<resource_link_id>\w+)$', 'mailing_list.api.set_access_level', name='api_lists_set_access_level'),
)
