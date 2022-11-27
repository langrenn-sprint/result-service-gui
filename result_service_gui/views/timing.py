"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    create_start_time_events,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
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
            informasjon = f"Velg funksjon i menyen. {informasjon}"
        try:
            valgt_heat = int(self.request.rel_url.query["heat"])
        except Exception:
            valgt_heat = 1

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            race = await RaceplansAdapter().get_race_by_order(
                user["token"], event_id, valgt_heat
            )
            races = []
            races.append(race)
            if len(races) > 0:
                for race in races:
                    # get start and finish list detail
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    race["finish_timings"] = await get_finish_timings(user, race["id"])
            else:
                informasjon = "Fant ingen heat. Velg på nytt."

            # get passeringer
            passeringer = await get_passeringer(user["token"], event_id, action)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "races": races,
                    "username": user["name"],
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

            if "finish" in action:
                informasjon = "Funksjon ikke støttet, bruk hovedside for tidtaker"
            elif "start" in action:
                informasjon = await create_start_time_events(user, form)  # type: ignore
            else:
                informasjon = "Ugylding action - ingen endringer"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&action={action}&heat={valgt_heat}"
        )


async def get_passeringer(token: str, event_id: str, action: str) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    if action == "control" or action == "Template":
        tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
            token, event_id
        )
        for passering in tmp_passeringer:
            if passering["timing_point"] == "Template":
                if action == "Template":
                    passeringer.append(passering)
            elif passering["status"] == "Error":
                if action == "control":
                    passeringer.append(passering)

    return passeringer
