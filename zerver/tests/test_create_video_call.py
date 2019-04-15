import json
import re
import httpretty

from zerver.lib.test_classes import ZulipTestCase

class TestFeedbackBot(ZulipTestCase):
    def setUp(self) -> None:
        user_profile = self.example_user('hamlet')
        self.login(user_profile.email, realm=user_profile.realm)

        httpretty.enable(allow_net_connect=False)

    def tearDown(self) -> None:
        httpretty.disable()
        httpretty.reset()

    def test_register_video_request_no_settings(self) -> None:
        with self.settings(VIDEO_ZOOM_CLIENT_ID=None):
            result = self.client_get("/json/calls/register_zoom_user")
            self.assert_json_error(result, "Zoom credentials have not been configured")

    def test_register_video_request(self) -> None:
        result = self.client_get("/json/calls/register_zoom_user")
        self.assertEqual(result.status_code, 302)

    def test_create_video_request_success(self) -> None:
        httpretty.register_uri(
            httpretty.POST,
            "https://api.zoom.us/oauth/token",
            body='{"access_token": "token"}'
        )

        httpretty.register_uri(
            httpretty.GET,
            "https://zoom.us/v2/users/me",
            body='{"id": "id"}'
        )

        httpretty.register_uri(
            httpretty.POST,
            re.compile("https://api.zoom.us/v2/users/.*/meetings"),
            body='{"join_url": "example.com"}'
        )

        result = self.client_get("/json/calls/complete_zoom_user?code=code")
        self.assert_json_success(result)

        result_dict = json.loads(result.content.decode('utf-8'))
        self.assertEqual(result_dict['url'], 'example.com')

    def test_create_video_request_query_error(self) -> None:
        result = self.client_get("/json/calls/complete_zoom_user")
        self.assert_json_error(result, "No code specified")

    def test_create_video_credential_error(self) -> None:
        httpretty.register_uri(
            httpretty.POST,
            "https://api.zoom.us/oauth/token",
            status=400
        )

        result = self.client_get("/json/calls/complete_zoom_user?code=code")
        self.assert_json_error(result, "Invalid Zoom credentials")

    def test_create_video_access_error(self) -> None:
        httpretty.register_uri(
            httpretty.POST,
            "https://api.zoom.us/oauth/token",
            body='{"access_token": "token"}'
        )

        httpretty.register_uri(
            httpretty.GET,
            "https://zoom.us/v2/users/me",
            status=400
        )

        result = self.client_get("/json/calls/complete_zoom_user?code=code")
        self.assert_json_error(result, "Invalid Zoom access token")

    def test_create_video_request_error(self) -> None:
        httpretty.register_uri(
            httpretty.POST,
            "https://api.zoom.us/oauth/token",
            body='{"access_token": "token"}'
        )

        httpretty.register_uri(
            httpretty.GET,
            "https://zoom.us/v2/users/me",
            body='{"id": "id"}'
        )

        httpretty.register_uri(
            httpretty.POST,
            re.compile("https://api.zoom.us/v2/users/.*/meetings"),
            status=400
        )

        result = self.client_get("/json/calls/complete_zoom_user?code=code")
        self.assert_json_error(result, "Invalid Zoom access token")
