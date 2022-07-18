"""Module for google photos adapter."""
import logging
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
import google_auth_oauthlib.flow
from multidict import MultiDict

GOOGLE_PHOTO_SERVER = "https://photoslibrary.googleapis.com/v1"
GOOGLE_PHOTO_SCOPE = "https://www.googleapis.com/auth/photoslibrary.readonly"
GOOGLE_PHOTO_CREDENTIALS_FILE = "/home/heming/github/photo_api_credentials.json"


class GooglePhotosAdapter:
    """Class representing google photos."""

    async def get_albums(self, token: str) -> List:
        """Get all albums."""
        albums = []
        servicename = "get_albums"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.get(
                f"{GOOGLE_PHOTO_SERVER}/albums", headers=headers
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    albums = await resp.json()
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {body}.")
        return albums

    async def get_auth_request_url(self, redirect_url: str, event_id: str) -> str:
        """Get auth URL for request to read from Photos API."""
        # Use the client_secret.json file to identify the application requesting
        # authorization. The client ID (from that file) and access scopes are required.
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            GOOGLE_PHOTO_CREDENTIALS_FILE, scopes=GOOGLE_PHOTO_SCOPE
        )

        # Indicate where the API server will redirect the user after the user completes
        # the authorization flow. The redirect URI is required. The value must exactly
        # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
        # configured in the API Console. If this value doesn't match an authorized URI,
        # you will get a 'redirect_uri_mismatch' error.
        flow.redirect_uri = redirect_url

        # Generate URL for request to Google's OAuth 2.0 server.
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            login_hint="info.renn.langrenn.kjelsaas@gmail.com",
            state=event_id,
            include_granted_scopes="true",
        )
        return authorization_url

    def get_token(self, redirect_url: str, event_id: str, user: dict) -> str:
        """Get token for request to read from Photos API."""
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            GOOGLE_PHOTO_CREDENTIALS_FILE, scopes=GOOGLE_PHOTO_SCOPE, state=event_id
        )
        flow.redirect_uri = redirect_url
        flow.fetch_token(code=user["g_client_id"])

        # Return the credentials.
        return flow.credentials.token
