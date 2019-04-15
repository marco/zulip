import requests
from typing import Any, Dict, Optional
from zerver.models import Realm

def request_zoom_video_call_url(access_key: str) -> Optional[Dict[str, Any]]:
    user_response = requests.get(
        "https://zoom.us/v2/users/me",
        headers = {
            "Authorization": "Bearer " + access_key,
        }
    )

    try:
        user_response.raise_for_status()
    except Exception:
        return None

    user_data = user_response.json()
    user_id = user_data["id"]

    response = requests.post(
        "https://api.zoom.us/v2/users/" + user_id + "/meetings",
        headers = {
            "Authorization": "Bearer " + access_key,
            "content-type": "application/json"
        },
        json = {}
    )

    try:
        response.raise_for_status()
    except Exception:
        return None

    return response.json()

def get_redirect_uri(realm: Realm) -> str:
    return realm.uri + "/json/calls/complete_zoom_user"

def request_register_zoom_user(
    api_key: str,
    api_secret: str,
    code: str,
    realm: Realm
) -> Optional[Dict[str, Any]]:
    response = requests.post(
        "https://api.zoom.us/oauth/token?grant_type=authorization_code&code="
        + code + "&redirect_uri=" + get_redirect_uri(realm),
        auth=(api_key, api_secret),
    )

    try:
        response.raise_for_status()
    except Exception:
        return None

    return response.json()
