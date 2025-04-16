"""Resource module for live resources."""

import logging
from operator import itemgetter

import aiohttp_jinja2
from aiohttp import web

from result_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceclassResultsService,
    RaceplansAdapter,
)

from .utils import (
    check_login_open,
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
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            user = await check_login_open(self)
            event = await get_event(user, event_id)
            races = []
            colseparators = []
            colclass = "w3-third"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""
                informasjon += "Velg klasse for å se live lister."
            try:
                valgt_startnr = int(self.request.rel_url.query["startnr"])
            except Exception:
                valgt_startnr = 0
            try:
                refresh = int(self.request.rel_url.query["refresh"])
            except Exception:
                refresh = 120

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            if valgt_klasse:
                races = await get_races(
                    user["token"], event_id, valgt_klasse, valgt_startnr, action
                )
                if len(races) == 0:
                    informasjon = f"{informasjon} Ingen kjøreplaner funnet."

                colseparators = get_colseparators(races)
                if len(colseparators) == 3:
                    colclass = "w3-quart"
                elif len(colseparators) == 4:
                    colclass = "w3-fifth"
                elif len(colseparators) == 5:
                    colclass = "w3-sixth"

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "live.html",
                self.request,
                {
                    "colclass": colclass,
                    "colseparators": colseparators,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "valgt_klasse": valgt_klasse,
                    "valgt_startnr": valgt_startnr,
                    "raceclasses": raceclasses,
                    "raceplan_summary": [],
                    "races": races,
                    "refresh": refresh,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


def get_colseparators(races: list) -> list:
    """Responsive design - determine column-arrangement."""
    colseparators = []
    i = len(races)
    if i > 16:
        colseparators.append(races[4]["order"])
        colseparators.append(races[8]["order"])
        colseparators.append(races[12]["order"])
        colseparators.append(races[16]["order"])
    elif i > 12:
        rest = 15 - i
        colseparators.append(races[4 - rest]["order"])
        colseparators.append(races[8 - rest]["order"])
        colseparators.append(races[12 - rest]["order"])
    elif i > 9:
        rest = 12 - i
        colseparators.append(races[3 - rest]["order"])
        colseparators.append(races[6 - rest]["order"])
        colseparators.append(races[9 - rest]["order"])
    elif i > 6:
        colseparators.append(races[2]["order"])
        colseparators.append(races[4]["order"])
        colseparators.append(races[6]["order"])
    elif i > 4:
        colseparators.append(races[2]["order"])
        colseparators.append(races[4]["order"])
    elif i > 2:
        colseparators.append(races[2]["order"])
    return colseparators


async def get_races(
    token: str, event_id: str, valgt_klasse: str, valgt_startnr: int, action: str
) -> list:
    """Get races for selected live view."""
    races = []

    if valgt_klasse:
        races = await get_races_for_live(
            token, event_id, valgt_klasse, valgt_startnr, action
        )
        # sort start list by starting position and append club_logo
        for race in races:
            if len(race["start_entries"]) > 1:
                race["start_entries"] = sorted(
                    race["start_entries"], key=itemgetter("starting_position")
                )
                for entry in race["start_entries"]:
                    entry["club_logo"] = EventsAdapter().get_club_logo_url(
                        entry["club"]
                    )
    return races


async def get_races_for_live(
    token: str, event_id: str, valgt_klasse: str, valgt_startnr: int, action: str
) -> list:
    """Extract races with enriched content for live view."""
    races = []
    _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )
    # first - get overview of races
    races_count_q = 0
    semi_results_registered = False
    for _tmp_race in _tmp_races:
        if _tmp_race["round"] == "Q":
            races_count_q += 1
        elif _tmp_race["round"] == "S":
            if len(_tmp_race["results"]) > 0:
                semi_results_registered = True
    for _tmp_race in _tmp_races:
        race = await RaceplansAdapter().get_race_by_id(token, _tmp_race["id"])
        race["finish_results"] = RaceclassResultsService().get_finish_rank_for_race(
            race, False
        )
        race["next_race"] = get_qualification_text(race)
        race["start_time"] = race["start_time"][-8:]
        # append race if selected starter is inside or not selected
        # optimize heats to show if more than 4 quarter finals
        # avoid quarter finals or finals, depending on semi final status
        if valgt_startnr == 0:
            if races_count_q > 4:
                if (semi_results_registered and race["round"] == "Q" and action != "all") or (
                    not semi_results_registered
                    and race["round"] == "F"
                    and action != "all"
                ):
                    pass
                else:
                    races.append(race)
            else:
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
