import json
import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from lti_school_permissions.decorators import lti_permission_required
from lti_tool.models import LtiRegistration
from lti_tool.types import LtiLaunch
from lti_tool.views import LtiLaunchBaseView

logger = logging.getLogger(__name__)


def lti_auth_error(request):
    raise PermissionDenied()


class ApplicationLaunchView(LtiLaunchBaseView):
    def handle_resource_launch(self, request, lti_launch):
        # For now, just log the launch and redirect to the Slack LTI tool index
        logger.info("Handling resource launch")
        logger.info(f"lti_launch: {lti_launch}")
        return lti_emailer_launch(request)

    def launch_setup(self, request: HttpRequest, lti_launch: LtiLaunch) -> None:
        # we want to just activate the deployment if it's not already active
        if not lti_launch.deployment.is_active:
            lti_launch.deployment.is_active = True
            lti_launch.deployment.save()


def config(request: HttpRequest, registration_uuid: str) -> JsonResponse:
    """
    Generate LTI 1.3 tool configuration JSON for Canvas integration.
    This view retrieves an existing LTI registration by UUID and generates a complete
    configuration that can be used to register the tool with Canvas. The configuration
    includes OIDC initiation URL, target link URI, JWKS URI, custom parameters, and
    placement settings for the LTI Emailer.

    The configuration automatically detects the environment (production, development,
    QA, local) based on the request domain and appends an appropriate suffix to the
    tool name in the UI.

    Parameters:
        request (HttpRequest): The Django HTTP request object
        registration_uuid (str): UUID string identifying the LTI registration
    Returns:
        JsonResponse: Tool configuration data in Canvas-compatible JSON format
    Raises:
        Returns a 400 status JsonResponse if the registration_uuid is not found
    """
    tool_domain = request.get_host()
    tool_name = "lti-emailer"
    tool_friendly_name = "Course Emailer"

    # Determine the Canvas environment based on the request domain
    def get_env_suffix(host: str) -> Optional[str]:
        # Production
        if host == f"{tool_name}.tlt.harvard.edu":
            return ""  # Production - no suffix
        # Development/QA
        elif host == f"{tool_name}.dev.tlt.harvard.edu":
            return " - DEV"
        elif host == f"{tool_name}.qa.tlt.harvard.edu":
            return " - QA"
        # Local development (any port)
        elif (
            host.startswith("localhost")
            or host.startswith("127.0.0.1")
            or host.startswith("local.tlt.harvard.edu")
        ):
            return " - LOCAL"
        else:
            return ""

    # Check for existing LtiRegistration by UUID for this issuer
    existing_registration: Optional[LtiRegistration] = LtiRegistration.objects.filter(
        uuid=registration_uuid
    ).first()
    if existing_registration:
        platform_registration = existing_registration
    else:
        logger.error(f"Provided registration_uuid {registration_uuid} not found.")
        return JsonResponse(
            {
                "error": f"Registration UUID {registration_uuid} not found.",
                "message": "Please make sure you are using a valid registration UUID or create a new registration in the Django admin interface.",
            },
            status=400,
        )

    # Construct the tool registration configuration
    jwks_uri = request.build_absolute_uri(reverse("jwks"))
    oidc_initiation_url = request.build_absolute_uri(
        reverse("init", args=[platform_registration.uuid])
    )
    target_link_uri = request.build_absolute_uri(reverse("launch"))

    description = "This LTI 1.3 tool provides an email list for the course and each section associated with the course site."
    env = get_env_suffix(tool_domain)

    # LTI Advantage scopes needed by this tool
    scopes = []

    # Custom parameters needed by this tool
    custom_parameters = {
        "canvas_course_id": "$Canvas.course.id",
        "canvas_course_sis_source_id": "$Canvas.course.sisSourceId",
        "context_label": "$com.instructure.contextLabel",
        "context_title": "$Context.title",
        "brand_config_js_url": "$com.instructure.brandConfigJS.url",
        "caliper_url": "$Caliper.url",
        "canvas_account_id": "$Canvas.account.id",
        "canvas_account_name": "$Canvas.account.name",
        "canvas_account_sis_id": "$Canvas.account.sisSourceId",
        "canvas_api_baseurl": "$Canvas.api.baseUrl",
        "canvas_api_domain": "$Canvas.api.domain",
        "canvas_group_contextids": "$Canvas.group.contextIds",
        "canvas_membership_permissions": "$Canvas.membership.permissions",
        "canvas_membership_roles": "$Canvas.membership.roles",
        "canvas_term_name": "$Canvas.term.name",
        "canvas_course_sectionsissourceids": "$Canvas.course.sectionSisSourceIds",
        "canvas_person_email_sis": "$vnd.Canvas.Person.email.sis",
        "canvas_masquerading_user_id": "$Canvas.masqueradingUser.id",
        "canvas_post_message_token": "$com.instructure.PostMessageToken",
        "canvas_user_adminable_accounts": "$Canvas.user.adminableAccounts",
        "canvas_user_id": "$Canvas.user.id",
        "canvas_user_is_root_account_admin": "$Canvas.user.isRootAccountAdmin",
        "canvas_user_loginid": "$Canvas.user.loginId",
        "canvas_user_prefers_high_contrast": "$Canvas.user.prefersHighContrast",
        "canvas_user_sisintegrationid": "$Canvas.user.sisIntegrationId",
        "canvas_user_sissourceid": "$Canvas.user.sisSourceId",
        "canvas_xapi_url": "$Canvas.xapi.url",
        "harvard_official_email": "$vnd.Canvas.Person.email.sis",
        "person_email_primary": "$Person.email.primary",
        "person_full_name": "$Person.name.full",
        "person_name_display": "$Person.name.display",
        "person_name_family": "$Person.name.family",
        "person_name_given": "$Person.name.given",
        "post_message_token": "$com.instructure.PostMessageToken",
    }

    # Permissions that are needed by this tool
    # permissions = "read_sis"

    tool_registration_config = {
        "title": f"{tool_friendly_name}{env}",
        "description": description,
        "oidc_initiation_url": oidc_initiation_url,
        # "oidc_initiation_urls": {},
        "target_link_uri": target_link_uri,
        "scopes": scopes,
        "extensions": [
            {
                "domain": tool_domain,
                "tool_id": f"{tool_name}-{platform_registration.uuid}",
                "platform": "canvas.instructure.com",
                "privacy_level": "public",
                "settings": {
                    "text": f"{tool_friendly_name}{env}",
                    "labels": {
                        "en": f"{tool_friendly_name}{env}",
                        "en-AU": f"{tool_friendly_name}{env}",
                        "es": f"{tool_friendly_name}{env}",
                        "zh-Hans": f"{tool_friendly_name}{env}",
                    },
                    # "icon_url": "https://some.icon.url/tool-level.png",
                    "placements": [
                        {
                            "text": f"{tool_friendly_name}{env}",
                            # "icon_url": "https://some.icon.url/my_dashboard.png",
                            "placement": "course_navigation",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": target_link_uri,
                            "canvas_icon_class": "icon-lti",
                            # "required_permissions": permissions,
                            "display_type": "full_width_in_context",
                            "default": "disabled",  # Tool is disabled by default
                        },
                    ],
                },
            }
        ],
        "public_jwk_url": jwks_uri,
        "custom_fields": custom_parameters,
    }

    return JsonResponse(tool_registration_config)


def not_authorized(request):
    """
    Returns a simple page that says the user is not authorized to view the requested page.
    """
    return HttpResponse("You are not authorized to view this page.", status=403)


@login_required
# @lti_role_required(const.TEACHING_STAFF_ROLES)
@lti_permission_required(settings.PERMISSION_LTI_EMAILER_VIEW)
# @require_http_methods(["POST"])
# @csrf_exempt
def lti_emailer_launch(request):
    logger.debug(
        "lti_emailer launched with params: %s",
        json.dumps(request.POST.dict(), indent=4),
    )
    return redirect("mailing_list:admin_index")
