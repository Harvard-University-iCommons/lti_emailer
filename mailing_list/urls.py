from django.conf.urls import url

from mailing_list import views, api


urlpatterns = [
    url(r'^admin_index$', views.admin_index, name='admin_index'),
    url(r'^list_members/(?P<section_id>\d+)$', views.list_members,
        name='list_members'),
    url(r'^api/lists$', api.lists, name='api_lists'),
    url(r'^api/lists/(?P<mailing_list_id>\d+)/set_access_level$',
        api.set_access_level, name='api_lists_set_access_level'),
]
