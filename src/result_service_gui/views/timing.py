"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    create_time_event,
    get_enchiced_startlist,
    get_event,
    update_time_event,
)


class Timing(web.View):
    """Class representing the start view."""

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
            informasjon = f"Velg modus for å se passeringer. {informasjon}"

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            passeringer = []
            startlist = []
            colclass = "w3-half"

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            valgt_klasse = ""
            startlist = await get_enchiced_startlist(
                user["token"], event_id, valgt_klasse
            )

            # get passeringer for klasse
            passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
                user["token"], event_id
            )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing.html",
                self.request,
                {
                    "action": action,
                    "colclass": colclass,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "startlist": startlist,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        logging.debug(user)

        informasjon = ""
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            action = str(form["action"])

            # Create new deltakere
            if "control" == action:
                informasjon = await update_time_event(user["token"], action, form)
            else:
                informasjon = await create_time_event(user["token"], action, form)
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&action={action}"
        )
