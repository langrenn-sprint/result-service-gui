"""Resource module for live resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_print,
)


class PrintLists(web.View):
    """Class representing the printable heat lists view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            races = []
            raceplan_summary = []
            html_template = "print_lists.html"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
                user["token"], event_id, valgt_klasse
            )
            if action == "raceplan":
                html_template = "print_raceplan.html"
                for race in _tmp_races:
                    if (race["raceclass"] == valgt_klasse) or ("" == valgt_klasse):
                        race["next_race"] = get_qualification_text(race)
                        race["start_time"] = race["start_time"][-8:]
                        races.append(race)
                raceplan_summary = get_raceplan_summary(_tmp_races, raceclasses)

            else:
                races = await get_races_for_print(
                    user, _tmp_races, raceclasses, valgt_klasse, action
                )
            if len(races) == 0:
                informasjon = "Ingen kjøreplaner funnet."

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                html_template,
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "username": user["username"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
