# Zoom Video Calling Oauth Configuration.

To set up a Zoom application, you'll need to do the following:

1. Visit the Zoom Marketplace here:
https://marketplace.zoom.us/develop/create.

2. Create a new application, and choose **Oauth** as the app type.
We recommend using a name like "ExampleCorp Zulip".

3. Select *account-level app* for the authentication type, disable
the option to publish the app in the Marketplace, and click **Create**.

4. Inside of the Zoom app management page, set the Redirect URL to e.g.
https://zulip.example.com/json/calls/complete_zoom_user.

5. Also set the "Scopes" to meeting:read:admin, meeting:write:admin,
and user:read:admin.

6. In /etc/zulip/zulip-secrets.conf, set `video_zoom_client_secret`
to be your app's "Client Secret".

7. In this file, set `VIDEO_ZOOM_CLIENT_ID` to your app's "Client ID".

