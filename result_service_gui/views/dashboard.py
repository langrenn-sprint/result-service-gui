"""Resource module for main view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_races_for_live_view,
)


EVENT_GUI_HOST_SERVER = os.getenv("EVENT_GUI_HOST_SERVER", "localhost")
EVENT_GUI_HOST_PORT = os.getenv("EVENT_GUI_HOST_PORT", "8080")
EVENT_GUI_URL = f"http://{EVENT_GUI_HOST_SERVER}:{EVENT_GUI_HOST_PORT}"


class Dashboard(web.View):
    """Class representing the main view."""

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
        valgt_heat = 0

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            races = await get_races_for_live_view(user, event_id, valgt_heat, 1)

            return await aiohttp_jinja2.render_template_async(
                "dashboard.html",
                self.request,
                {
                    "lopsinfo": "Dashboard - under rennet",
                    "event": event,
                    "event_gui_url": EVENT_GUI_URL,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "races": races,
                    "username": user["username"],
                    "valgt_heat": valgt_heat,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
