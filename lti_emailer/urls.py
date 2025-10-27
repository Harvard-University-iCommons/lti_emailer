import watchman.views
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from lti_tool.views import OIDCLoginInitView, jwks

from lti_emailer import views
from lti_emailer.views import ApplicationLaunchView, config, not_authorized

urlpatterns = [
    path("admin/", admin.site.urls),
    path(".well-known/jwks.json", jwks, name="jwks"),
    path("init/<uuid:registration_uuid>/", OIDCLoginInitView.as_view(), name="init"),
    path("config/<uuid:registration_uuid>/", config, name="config"),
    path("launch/", ApplicationLaunchView.as_view(), name="launch"),
    path("not_authorized", not_authorized, name="not_authorized"),
    path("lti_auth_error/", views.lti_auth_error, name="lti_auth_error"),
    re_path(
        r"^mailing_list/",
        include(("mailing_list.urls", "mailing_list"), namespace="mailing_list"),
    ),
    re_path(r"^mailgun/", include(("mailgun.urls", "mailgun"), namespace="mailgun")),
    path("w/", include("watchman.urls")),
    re_path(r"^status/?$", watchman.views.bare_status),
]

if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            re_path(r"^__debug__/", include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass  # This is OK for a deployed instance running in DEBUG mode
