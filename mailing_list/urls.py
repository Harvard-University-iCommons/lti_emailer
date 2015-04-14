from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(r'^index/(?P<resource_link_id>\w+)$', 'mailing_list.views.index', name='index'),
    url(r'^api/lists/(?P<resource_link_id>\w+)$', 'mailing_list.api.lists', name='api_lists'),
    url(r'^api/lists/(?P<mailing_list_id>\d+)/set_access_level/(?P<resource_link_id>\w+)$', 'mailing_list.api.set_access_level', name='api_lists_set_access_level'),
)
