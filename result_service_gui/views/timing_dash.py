"""Resource module for Timing Dashboard view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from result_service_gui.services import (
    ConfigAdapter,
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
                    "service_status": await get_service_status(user["token"], event_id),
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def get_service_status(token: str, event_id: str) -> dict:
    """Get config details from db."""
    integration_available = await ConfigAdapter().get_config(
        token, event_id, "INTEGRATION_SERVICE_AVAILABLE"
    )
    integration_running = await ConfigAdapter().get_config_bool(
        token, event_id, "INTEGRATION_SERVICE_RUNNING"
    )
    integration_start = await ConfigAdapter().get_config_bool(
        token, event_id, "INTEGRATION_SERVICE_START"
    )
    integration_mode = await ConfigAdapter().get_config(
        token, event_id, "INTEGRATION_SERVICE_MODE"
    )
    return {
        "integration_available": integration_available,
        "integration_running": integration_running,
        "integration_start": integration_start,
        "integration_mode": integration_mode,
    }
