from django.urls import path, re_path

from mailing_list import views, api


urlpatterns = [
    path('admin_index/', views.admin_index, name='admin_index'),
    re_path(r'^list_members/(?P<section_id>\d+)/', views.list_members, name='list_members'),
    re_path(r'^list_members/', views.list_members, name='list_members_no_id'),
    re_path(r'^api/lists/(?P<mailing_list_id>\d+)/set_access_level/', api.set_access_level, name='api_lists_set_access_level'),
    re_path(r'^api/lists/', api.lists, name='api_lists'),
    re_path(r'^api/course_settings/', api.get_or_create_course_settings, name='api_course_settings'),
]
