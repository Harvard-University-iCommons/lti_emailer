from django.urls import path, re_path, include
from django.conf import settings
import watchman.views

from lti_emailer import views
from icommons_ui import views as icommons_ui_views


urlpatterns = [
    path('lti_auth_error/', views.lti_auth_error, name='lti_auth_error'),
    path('tool_config/', views.tool_config, name='tool_config'),
    path('lti_launch', views.lti_launch, name='lti_launch'),
    re_path(r'^mailing_list/', include(('mailing_list.urls', 'mailing_list'), namespace='mailing_list')),
    re_path(r'^mailgun/', include(('mailgun.urls', 'mailgun'), namespace='mailgun')),
    path('not_authorized/', icommons_ui_views.not_authorized, name="not_authorized"),
    path('w/', include('watchman.urls')),
    re_path(r'^status/?$', watchman.views.bare_status),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            re_path(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass  # This is OK for a deployed instance running in DEBUG mode
