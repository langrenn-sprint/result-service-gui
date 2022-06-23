"""Resource module for photo admin view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import GooglePhotosAdapter
from .utils import (
    check_login,
    get_event,
    get_local_time,
)


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
            user = await check_login(self)
            event = await get_event(user, event_id)
            albums = await GooglePhotosAdapter().get_albums()

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
