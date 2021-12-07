"""Resource module for verificatoin of timing registration."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    create_time_event,
    get_enchiced_startlist,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
)


class TimingVerify(web.View):
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
            valgt_heat = self.request.rel_url.query["valgt_heat"]
            valgt_runde = self.request.rel_url.query["valgt_runde"]
        except Exception:
            valgt_heat = ""
            valgt_runde = ""

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            races = await RaceplansAdapter().get_all_races(user["token"], event_id)
            raceplan_summary = []
            if len(races) == 0:
                informasjon = f"{informasjon} Ingen kjøreplaner funnet."
            else:
                raceplan_summary = get_raceplan_summary(races, raceclasses)
            # generate text explaining qualificatoin rule (videre til)
            for race in races:
                race["next_race"] = get_qualification_text(race)

            if len(races) > 0:
                for race in races:
                    # get start list detail
                    race["startliste"] = await get_enchiced_startlist(
                        user, race["id"], race["start_entries"]
                    )
            else:
                informasjon = "Fant ingen heat. Velg på nytt."

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing_verify.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "username": user["username"],
                    "valgt_heat": valgt_heat,
                    "valgt_runde": valgt_runde,
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

            informasjon = await create_time_event(user, action, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/timing_verify?event_id={event_id}&informasjon={informasjon}&action={action}&heat={valgt_heat}"
        )
