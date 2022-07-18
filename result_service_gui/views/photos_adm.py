"""Resource module for photo admin view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import GooglePhotosAdapter
from .utils import (
    check_login_google,
    get_auth_url_google_photos,
    get_event,
    get_local_time,
    login_google_photos,
)

WEBSERVER_PHOTO_URL = "http://localhost:8090/photo_adm"


class PhotosAdm(web.View):
    """Class representing the photo admin view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login_google(self, event_id)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            if not user["g_auth_photos"]:
                if event_id == "":
                    # handle authorization response from google photo
                    event_id = self.request.rel_url.query["state"]
                    user["g_scope"] = self.request.rel_url.query["scope"]
                    user["g_client_id"] = self.request.rel_url.query["code"]
                    result = await login_google_photos(
                        self, WEBSERVER_PHOTO_URL, event_id, user
                    )
                    if result == 200:
                        # reload user session information
                        user = await check_login_google(self, event_id)
                    else:
                        raise Exception(
                            f"Det har oppstått en feil med google autorisasjon - {result}"
                        )
                else:
                    # initiate authorization for google photo
                    auth_url = await get_auth_url_google_photos(
                        self, WEBSERVER_PHOTO_URL, event_id
                    )
                    if auth_url != "":
                        return web.HTTPSeeOther(location=f"{auth_url}")
            event = await get_event(user, event_id)

            albums = await GooglePhotosAdapter().get_albums(user["g_photos_token"])

            return await aiohttp_jinja2.render_template_async(
                "photo_adm.html",
                self.request,
                {
                    "lopsinfo": "Foto administrasjon",
                    "albums": albums,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": get_local_time("HH:MM"),
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
