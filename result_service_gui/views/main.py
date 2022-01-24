"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import EventsAdapter
from .utils import check_login_open, get_event


class Main(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login_open(self)
            event = await get_event(user["token"], "")

            events = await EventsAdapter().get_all_events(user["token"])
            logging.debug(f"Events: {events}")

            return await aiohttp_jinja2.render_template_async(
                "index.html",
                self.request,
                {
                    "lopsinfo": "Langrenn-sprint",
                    "event": event,
                    "event_id": "",
                    "events": events,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to login page.")
            return web.HTTPSeeOther(location=f"/login?informasjon={e}")
