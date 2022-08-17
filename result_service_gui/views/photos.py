"""Resource module for photo resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    FotoService,
    PhotosAdapter,
    RaceclassesAdapter,
)
from .utils import (
    check_login_open,
    get_event,
)


class Photos(web.View):
    """Class representing the photo view."""

    async def get(self) -> web.Response:
        """Get route function that return the photolister page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            user = await check_login_open(self)
            event = await get_event(user, event_id)

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
            try:
                valgt_startnr = int(self.request.rel_url.query["startnr"])
            except Exception:
                valgt_startnr = 0

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            photos = []
            if valgt_klasse == "":
                photos = await PhotosAdapter().get_all_photos(user["token"], event_id)
            else:
                photos = await FotoService().get_photo_by_raceclass(
                    user["token"], event_id, valgt_klasse
                )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "photos.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "photos": photos,
                    "valgt_klasse": valgt_klasse,
                    "valgt_startnr": valgt_startnr,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
