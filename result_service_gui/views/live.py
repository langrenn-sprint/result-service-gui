"""Resource module for live resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_qualification_text,
)


class Live(web.View):
    """Class representing the live view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
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

            races = []
            contestants = []
            colclass = "w3-half"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
                informasjon += "Velg klasse for å se live lister."
            try:
                valgt_startnr = int(self.request.rel_url.query["startnr"])
            except Exception:
                valgt_startnr = 0

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            colseparators = []
            colclass = "w3-third"
            if valgt_klasse != "":
                contestants = (
                    await ContestantsAdapter().get_all_contestants_by_raceclass(
                        user["token"], event_id, valgt_klasse
                    )
                )

                races = await get_races_for_live(
                    user["token"], event_id, valgt_klasse, valgt_startnr
                )
                if len(races) == 0:
                    informasjon = f"{informasjon} Ingen kjøreplaner funnet."

                colseparators = get_colseparators(races)
                if len(colseparators) == 3:
                    colclass = "w3-quart"
                else:
                    colclass = "w3-third"

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "live.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "valgt_startnr": valgt_startnr,
                    "colseparators": colseparators,
                    "colclass": colclass,
                    "contestants": contestants,
                    "raceclasses": raceclasses,
                    "races": races,
                    "username": user["username"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


def get_colseparators(races: list) -> list:
    """Responsive design - determine column-arrangement."""
    colseparators = []
    i = 0
    icolcount = 1
    for heat in races:
        i += 1
        if heat["round"] == "S" and icolcount == 1:
            icolcount += 1
            colseparators.append(heat["order"])
        elif heat["round"] == "F" and icolcount == 2:
            icolcount += 1
            colseparators.append(heat["order"])
        elif i > 4 and icolcount == 1:
            icolcount += 1
            colseparators.append(heat["order"])
        elif i > 8 and icolcount == 2:
            icolcount += 1
            colseparators.append(heat["order"])
        elif i > 12 and icolcount == 3:
            icolcount += 1
            colseparators.append(heat["order"])
        elif i > 16 and icolcount == 4:
            icolcount += 1
            colseparators.append(heat["order"])
    return colseparators


def get_finish_rank(race: dict) -> list:
    """Extract timing events from finish."""
    finish_rank = []
    results = race["results"]
    if len(results) > 0:
        logging.debug(f"Resultst: {results}")
        if "Finish" in results.keys():
            finish_results = results["Finish"]
            if len(finish_results) > 0:
                logging.debug(finish_results.keys())
                if "ranking_sequence" in finish_results.keys():
                    finish_ranks = finish_results["ranking_sequence"]
                    race["finish_results"] = []
                    for rank_event in finish_ranks:
                        finish_rank.append(rank_event)
    return finish_rank


async def get_races_for_live(
    token: str, event_id: str, valgt_klasse: str, valgt_startnr: int
) -> list:
    """Extract races with enriched content for live view."""
    races = []
    _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )
    for _tmp_race in _tmp_races:
        if _tmp_race["raceclass"] == valgt_klasse:
            race = await RaceplansAdapter().get_race_by_id(token, _tmp_race["id"])
            race["finish_results"] = get_finish_rank(race)
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            # append race if selected starter is inside or not selected
            if valgt_startnr == 0:
                races.append(race)
            else:
                appended = False
                for entry in race["start_entries"]:
                    if entry["bib"] == valgt_startnr:
                        races.append(race)
                        appended = True
                if not appended:
                    for entry in race["finish_results"]:
                        if entry["bib"] == valgt_startnr:
                            races.append(race)
    return races
