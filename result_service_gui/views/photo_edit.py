"""Resource module for photo edit view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import GooglePhotosAdapter
from .utils import (
    check_login_google_photos,
    get_event,
    get_local_time,
)


class PhotoEdit(web.View):
    """Class representing the photo edit view."""

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
            album_id = self.request.rel_url.query["album_id"]
            album_title = self.request.rel_url.query["album_title"]
        except Exception:
            album_id = ""
            album_title = ""

        try:
            user = await check_login_google_photos(self)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            event = await get_event(user, event_id)
            album = await GooglePhotosAdapter().get_album_items(
                user["g_photos_token"], album_id
            )

            return await aiohttp_jinja2.render_template_async(
                "photo_edit.html",
                self.request,
                {
                    "lopsinfo": album_title,
                    "album": album,
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
