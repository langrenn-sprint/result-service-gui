"""Resource module for Timing Dashboard view."""

import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_race_kpis,
)


class TimingDash(web.View):
    """Class representing the TimingDash view."""

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

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            raceplan_kpis = await get_race_kpis(user["token"], event, raceclasses, "A")

            return await aiohttp_jinja2.render_template_async(
                "timing_dash.html",
                self.request,
                {
                    "lopsinfo": "Tidtaker: Dashboard",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "raceclasses": raceclasses,
                    "raceplan_kpis": raceplan_kpis,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
