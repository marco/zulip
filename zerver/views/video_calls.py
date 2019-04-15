from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.conf import settings
from zerver.decorator import has_request_variables
from zerver.lib.response import json_success, json_error
from zerver.lib.video_calls import request_register_zoom_user, request_zoom_video_call_url, get_redirect_uri
from zerver.models import UserProfile

@has_request_variables
def register_zoom_user(request: HttpRequest, user_profile: UserProfile) -> HttpResponse:
    if settings.VIDEO_ZOOM_CLIENT_ID is None:
        return json_error(_("Zoom credentials have not been configured"))

    return HttpResponseRedirect(
        "https://zoom.us/oauth/authorize?response_type=code&client_id="
        + settings.VIDEO_ZOOM_CLIENT_ID
        + "&redirect_uri="
        + get_redirect_uri(user_profile.realm)
    )

@has_request_variables
def complete_zoom_user(request: HttpRequest, user_profile: UserProfile) -> HttpResponse:
    if "code" not in request.GET:
        return json_error(_("No code specified"))

    registration = request_register_zoom_user(
        settings.VIDEO_ZOOM_CLIENT_ID,
        settings.VIDEO_ZOOM_CLIENT_SECRET,
        request.GET["code"],
        user_profile.realm
    )

    if registration is None or "access_token" not in registration:
        return json_error(_("Invalid Zoom credentials"))

    videoResponse = request_zoom_video_call_url(registration["access_token"])

    if videoResponse is None or "join_url" not in videoResponse:
        return json_error(_("Invalid Zoom access token"))

    return json_success({"url": videoResponse["join_url"]})

@has_request_variables
def deregister_zoom_user(request: HttpRequest, user_profile: UserProfile) -> HttpResponse:
    return json_success()
