"""Resource module for control resources."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    get_event,
    update_time_event,
)

EVENT_GUI_HOST_SERVER = os.getenv("EVENT_GUI_HOST_SERVER", "localhost")
EVENT_GUI_HOST_PORT = os.getenv("EVENT_GUI_HOST_PORT", "8080")
EVENT_GUI_URL = f"http://{EVENT_GUI_HOST_SERVER}:{EVENT_GUI_HOST_PORT}"


class Control(web.View):
    """Class representing the control view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
            informasjon = f"Velg funksjon. {informasjon}"
        try:
            valgt_heat = int(self.request.rel_url.query["heat"])
        except Exception:
            valgt_heat = 0

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            colclass = "w3-half"

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # get passeringer
            passeringer = await get_passeringer(user["token"], event_id, action)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "control.html",
                self.request,
                {
                    "action": action,
                    "colclass": colclass,
                    "event": event,
                    "event_id": event_id,
                    "event_gui_url": EVENT_GUI_URL,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "username": user["username"],
                    "valgt_heat": valgt_heat,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            action = str(form["action"])
            valgt_heat = str(form["heat"])

            informasjon = await update_time_event(user, action, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&action={action}&heat={valgt_heat}"
        )


async def get_passeringer(token: str, event_id: str, action: str) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    if action == "control" or action == "template":
        tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
            token, event_id
        )
        for passering in tmp_passeringer:
            if passering["timing_point"] == "Template":
                if action == "template":
                    passeringer.append(passering)
            elif passering["status"] == "Error":
                if action == "control":
                    passeringer.append(passering)

    return passeringer
