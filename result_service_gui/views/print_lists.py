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
    get_races_for_round_result,
    get_results_by_raceclass,
)


class PrintLists(web.View):
    """Class representing the printable heat lists view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        try:
            user = await check_login(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user, event_id)

            races = []
            raceplan_summary = []
            resultlist = []
            html_template = "print_lists.html"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
            try:
                valgt_runde = self.request.rel_url.query["runde"]
            except Exception:
                valgt_runde = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
                user["token"], event_id, valgt_klasse
            )
            if action == "raceplan":
                html_template = "print_raceplan.html"
                raceplan_summary = get_raceplan_summary(_tmp_races, raceclasses)

            elif action == "result":
                resultlist = await get_results_by_raceclass(
                    user, event_id, valgt_klasse
                )
                html_template = "print_results.html"

            races = await get_races(
                user,
                action,
                valgt_klasse,
                valgt_runde,
                _tmp_races,
                raceclasses,
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
                    "valgt_runde": valgt_runde,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "races": races,
                    "resultlist": resultlist,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def get_races(
    user: dict,
    action: str,
    valgt_klasse: str,
    valgt_runde: str,
    _tmp_races: list,
    raceclasses: list,
) -> list:
    """Get races to display - return sorted list."""
    races = []
    if action == "raceplan":
        for race in _tmp_races:
            if (race["raceclass"] == valgt_klasse) or ("" == valgt_klasse):
                race["next_race"] = get_qualification_text(race)
                race["start_time"] = race["start_time"][-8:]
                races.append(race)
    elif action == "round_result":
        races = await get_races_for_round_result(
            user, _tmp_races, valgt_runde, valgt_klasse
        )
    else:
        races = await get_races_for_print(
            user, _tmp_races, raceclasses, valgt_klasse, action
        )
    return races
