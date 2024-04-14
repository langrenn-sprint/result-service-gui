"""Resource module for Timing Dashboard view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_raceplan_summary,
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
            raceplan_kpis = await get_race_kpis(user["token"], event, raceclasses)

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


async def get_race_kpis(token: str, event: dict, raceclasses: list) -> list:
    """Generate a summary with key performance indicators for race execution."""
    summary_kpis = []
    all_races = await RaceplansAdapter().get_all_races(token, event['id'])
    raceplan_summary = get_raceplan_summary(all_races, raceclasses)

    # enrich with race details
    for raceclass in raceplan_summary:
        races = await RaceplansAdapter().get_races_by_racesclass(token, event['id'], raceclass['name'])
        races_q = []
        races_s = []
        races_f = []
        for race in races:
            # calculate key kpis pr race
            race_summary = get_race_summary(event, race)

            if race['round'] in ["Q", "R1"]:
                races_q.append(race_summary)
            elif race['round'] in ["S", "R2"]:
                races_s.append(race_summary)
            elif race['round'] == "F":
                races_f.append(race_summary)
        raceclass['races_q'] = races_q
        raceclass['races_s'] = races_s
        raceclass['races_f'] = races_f
        raceclass['progress'] = get_raceclass_progress(races_q, races_s, races_f)

        summary_kpis.append(raceclass)
    return summary_kpis


def get_raceclass_progress(races_q: list, races_s: list, races_f: list) -> int:
    """Calculate overal progress of race execution."""
    raceclass_progress = 1
    # 1 not started
    # 2 not started - with DNS */
    # 3 started - no results */
    # 4 partial results - with DNF */
    # 5 all results ok */
    # 6 error in race results */
    for race in races_f:
        if race['progress'] > raceclass_progress:
            raceclass_progress = race['progress']
        if race['progress'] in [4, 6]:
            return race['progress']  # partial or error results
    for race in races_s:
        if race['progress'] > raceclass_progress:
            raceclass_progress = race['progress']
        if race['progress'] in [4, 6]:
            return race['progress']  # partial or error results
    for race in races_q:
        if race['progress'] > raceclass_progress:
            raceclass_progress = race['progress']
        if race['progress'] in [4, 6]:
            return race['progress']  # partial or error results
    return raceclass_progress


def get_race_summary(event: dict, race: dict) -> dict:
    """Calculate key kpis for a single race."""
    try:
        count_starts = len(race['start_entries'])
    except Exception:
        count_starts = 0
    try:
        count_results = len(race['results']['Finish']['ranking_sequence'])
    except Exception:
        count_results = 0
    try:
        count_dns = len(race['results']['DNS']['ranking_sequence'])
    except Exception:
        count_dns = 0
    try:
        count_dnf = len(race['results']['DNF']['ranking_sequence'])
    except Exception:
        count_dnf = 0

    race_progress = get_race_progress(event, race, count_starts, count_dns, count_dnf, count_results)

    if event['competition_format'] != "Individual Sprint":
        race_name = event['competition_format']
    elif race["round"] == "F":
        race_name = f"{race['round']}{race['index']}"
    else:
        race_name = f"{race['round']}{race['index']}{race['heat']}"

    race_summary = {
        "name": race_name,
        "order": race["order"],
        "count_starts": count_starts,
        "count_results": count_results,
        "count_dns": count_dns,
        "count_dnf": count_dnf,
        "progress": race_progress,
        "start_time": race["start_time"][-8:]
    }
    return race_summary


def get_race_progress(event: dict, race: dict, count_starts: int, count_dns: int, count_dnf: int, count_results: int) -> int:
    """Evaluate race progress and return a code to indicate coloring in dashboard."""
    progress = 6
    # 1 not started
    # 2 not started - with DNS */
    # 3 started - no results */
    # 4 partial results - with DNF */
    # 5 all results ok */
    # 6 error in race results */
    time_now = EventsAdapter().get_local_time(event, "log")
    start_time = race["start_time"]
    if start_time > time_now:
        if count_results > 0:
            progress = 6
        elif count_dnf > 0:
            progress = 6
        elif count_dns == 0:
            progress = 1
        else:
            progress = 2
    elif count_results == 0:
        if count_starts == 0:
            progress = 5
        else:
            progress = 3
    elif (count_results + count_dns + count_dnf) < count_starts:
        progress = 4
    elif (count_results + count_dns + count_dnf) > count_starts:
        progress = 6
    else:
        progress = 5
    return progress
