"""Utilities module for gui services."""

import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    RaceclassResultsService,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check login and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        raise web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {
        "name": session["name"],
        "loggedin": True,
        "token": session["token"],
    }


async def check_login_open(self) -> dict:
    """Check login and return credentials."""
    user = {}
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if loggedin:
        user = {
            "name": session["name"],
            "loggedin": True,
            "token": session["token"],
        }
    else:
        user = {"name": "Gjest", "loggedin": False, "token": ""}

    return user


def get_display_style(start_time: str, event: dict) -> str:
    """Calculate time remaining to start and return table header style."""
    time_now = EventsAdapter().get_local_datetime_now(event)
    start_time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
    # make sure timezone is correct
    start_time_obj = start_time_obj.replace(tzinfo=time_now.tzinfo)
    delta_time = start_time_obj - time_now
    delta_seconds = delta_time.total_seconds()
    display_style = ""
    if delta_seconds < 300:
        display_style = "table_header_green"
    elif delta_seconds < 600:
        display_style = "table_header_orange"
    else:
        display_style = "headerblue"

    return display_style


async def get_enrichced_startlist(user: dict, race: dict) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    i = 0
    # get time-events registered
    next_race_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race["id"]
    )
    if race["start_entries"]:
        for start_entry in race["start_entries"]:
            start_entry["club_logo"] = EventsAdapter().get_club_logo_url(
                start_entry["club"]
            )
            i += 1
            for time_event in next_race_time_events:
                # get next race info
                if time_event["timing_point"] == "Template":
                    logging.debug(f"Time_event with error - {time_event}")
                elif time_event["timing_point"] == "Template":
                    if i == time_event["rank"]:
                        if time_event["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry["next_race"] = time_event["next_race"]
                # check if start, DNS or DNF is registered
                elif time_event["timing_point"] in ["Start", "DNS", "DNF"]:
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["status"] = time_event["timing_point"]
                        start_entry["status_id"] = time_event["id"]
            startlist.append(start_entry)
    return startlist


async def get_finish_timings(user: dict, race_id: str) -> list:
    """Get finish events for race, Template event if no result is registered."""
    finish_events = []
    race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)

    # get time-events registered
    time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race_id
    )
    found_events = 0
    for i in range(1, race["max_no_of_contestants"] + 1):
        for time_event in time_events:
            if time_event["timing_point"] == "Finish" and time_event["status"] == "OK":
                if i == time_event["rank"]:
                    found_events += 1
                    finish_events.append(time_event)
        if found_events == 0:
            if race["round"] == "F":
                dummy_event = {"rank": i}
                finish_events.append(dummy_event)
            else:
                for time_event in time_events:
                    if (time_event["timing_point"] == "Template") and (
                        i == time_event["rank"]
                    ):
                        finish_events.append(time_event)
                        break
        else:
            found_events = found_events - 1
    return finish_events


async def get_event(user: dict, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Langrenn-sprint", "organiser": "Ikke valgt"}
    if event_id:
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(user["token"], event_id)

    return event


async def get_passeringer(
    token: str, event_id: str, action: str, valgt_klasse: str
) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    _tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
        token, event_id
    )

    # filter based upon raceclass
    tmp_passeringer = []
    for passering in _tmp_passeringer:
        if passering["race"].startswith(valgt_klasse):
            tmp_passeringer.append(passering)

    if action == "control":
        for passering in reversed(tmp_passeringer):
            if not valgt_klasse or valgt_klasse in passering["race"]:
                if (
                    passering["status"] == "Error"
                    and passering["timing_point"] != "Template"
                ):
                    passeringer.append(passering)
    elif action in ["Template", "DNS"]:
        for passering in tmp_passeringer:
            if valgt_klasse in passering["race"]:
                if passering["timing_point"] == action:
                    passeringer.append(passering)
    else:
        for passering in tmp_passeringer:
            if passering["timing_point"] not in [
                "Template",
                "Error",
            ]:
                passeringer.append(passering)

    # indentify last passering in race
    i = 0
    last_race = ""
    for passering in passeringer:
        if i == 0:
            passering["first_in_heat"] = True
        elif last_race != passering["race"]:
            passeringer[i - 1]["last_in_heat"] = True
            passering["first_in_heat"] = True
        i += 1
        if i == len(passeringer):
            passering["last_in_heat"] = True
        last_race = passering["race"]

    # sort by time
    def myfunc(n) -> str:
        return n["registration_time"]

    passeringer.sort(key=myfunc)
    passeringer.reverse()

    return passeringer


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] in ["R2", "F"]:
        text = ""
    else:
        for key, value in race["rule"].items():
            if key == "S":
                for x, y in value.items():
                    if y == "REST":
                        text += f"Resten til semi {x}. "
                    elif y > 0:
                        text += f"{y} til semi {x}. "
            elif key == "F":
                for x, y in value.items():
                    if y == "ALL":
                        text += f"Alle til finale {x}. "
                    elif y == "REST":
                        text += f"Resten til finale {x}. "
                    elif y > 0:
                        text += f"{y} til finale {x}. "
    logging.debug(f"Regel hele: {text}")
    return text


async def get_race_id_by_name(
    user: dict, event_id: str, next_race: str, raceclass: str
) -> str:
    """Get race_id for a given race."""
    race_id = ""
    races = await RaceplansAdapter().get_races_by_racesclass(
        user["token"], event_id, raceclass
    )
    for race in races:
        tmp_next_race = f"{race['round']}{race['index']}{race['heat']}"
        if next_race == tmp_next_race:
            return race["id"]
    return race_id


def get_raceplan_summary(races: list, raceclasses: list) -> list:
    """Generate a summary with key timing for the raceplan."""
    summary = []
    # create a dict of all raceclasses and populate
    # loop raceclasses and find key parameters
    for raceclass in raceclasses:
        class_summary = {"name": raceclass["name"]}
        class_summary["no_of_contestants"] = raceclass["no_of_contestants"]
        class_summary["ranking"] = raceclass["ranking"]
        # loop through races - update start time pr round pr class
        for race in reversed(races):
            if race["raceclass"] == raceclass["name"]:
                if race["round"] in ["Q", "R1"]:
                    class_summary["timeQ"] = race["start_time"][-8:]
                    class_summary["orderQ"] = race["order"]
                elif race["round"] in ["S", "R2"]:
                    class_summary["timeS"] = race["start_time"][-8:]
                    class_summary["orderS"] = race["order"]
                elif race["round"] == "F":
                    class_summary["timeF"] = race["start_time"][-8:]
                    class_summary["orderF"] = race["order"]
        summary.append(class_summary)
    logging.debug(summary)
    return summary


def get_races_for_live_view(
    event: dict, races: list, valgt_heat: int, number_of_races: int
) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    i = 0
    time_now = EventsAdapter().get_local_time(event, "log")
    # find next race on start
    if valgt_heat == 0:
        for race in races:
            if time_now < race["start_time"]:
                valgt_heat = race["order"]
                break
        else:
            if valgt_heat == 0:
                # all races have already started
                valgt_heat = len(races) + 1

    for race in races:
        # from heat number (order) if selected
        if (race["order"] >= valgt_heat) and (i < number_of_races):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1

    return filtered_racelist


async def get_races_for_print(
    user: dict, _tmp_races: list, raceclasses: list, valgt_klasse: str, action: str
) -> list:
    """Get races with lists - formatted for print."""
    races = []
    for race in _tmp_races:
        for raceclass in raceclasses:
            if race["raceclass"] == raceclass["name"]:
                if (race["raceclass"] == valgt_klasse) or (valgt_klasse == ""):
                    race = await RaceplansAdapter().get_race_by_id(
                        user["token"], race["id"]
                    )
                    race["next_race"] = get_qualification_text(race)
                    race["start_time"] = race["start_time"][-8:]
                    # get start list details
                    if action == "live":
                        race["list_type"] = "start"
                        if race["results"]:
                            if "Finish" in race["results"]:
                                race["list_type"] = "result"
                    else:
                        race["list_type"] = action

                    if race["list_type"] == "start":
                        race["startliste"] = await get_enrichced_startlist(user, race)
                    else:
                        race["finish_results"] = (
                            RaceclassResultsService().get_finish_rank_for_race(
                                race, False
                            )
                        )
                    races.append(race)
    return races


async def get_races_for_round_result(
    user: dict, _tmp_races: list, valgt_runde: str, valgt_klasse: str, action: str
) -> list:
    """Get races for a given round - formatted for print."""
    races = []
    next_round = []
    if valgt_runde == "Q":
        next_round = ["S", "F"]
    elif valgt_runde == "S":
        next_round = ["F"]

    for race in _tmp_races:
        if race["raceclass"] == valgt_klasse:
            race = await RaceplansAdapter().get_race_by_id(user["token"], race["id"])
            race["start_time"] = race["start_time"][-8:]
            if valgt_runde in ["", race["round"]]:
                if action.count("result") > 0:
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "result"
                    race["finish_results"] = (
                        RaceclassResultsService().get_finish_rank_for_race(race, False)
                    )
                    races.append(race)
            elif race["round"] in next_round:
                if action.count("start") > 0:
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "start"
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    races.append(race)
    return races


async def create_start(user: dict, form: dict) -> str:
    """Extract form data and create one start."""
    bib = int(form["bib"])
    contestant = await ContestantsAdapter().get_contestant_by_bib(
        user["token"], form["event_id"], bib
    )
    if contestant:
        new_race_info = await get_new_race_info(user, form)
        new_start = {
            "startlist_id": new_race_info["startlist_id"],
            "race_id": new_race_info["race_id"],
            "bib": bib,
            "starting_position": new_race_info["starting_position"],
            "scheduled_start_time": new_race_info["start_time"],
            "name": f"{contestant['first_name']} {contestant['last_name']}",
            "club": contestant["club"],
        }
        # validation - check that bib not already is in start entry for round
        new_race = await RaceplansAdapter().get_race_by_id(
            user["token"], new_start["race_id"]
        )
        start_entries = await StartAdapter().get_start_entries_by_bib(
            user["token"], form["event_id"], bib
        )
        for start_entry in start_entries:
            race = await RaceplansAdapter().get_race_by_id(
                user["token"], start_entry["race_id"]
            )
            if new_race["round"] == race["round"]:
                raise web.HTTPBadRequest(
                    reason=f"405 Bib already exists in round - {race['round']}"
                )

        await StartAdapter().create_start_entry(user["token"], new_start)
        informasjon = f"Lagt til nr {bib}"

        # update previous result with correct "videre til"
        time_events = await TimeEventsAdapter().get_time_events_by_event_id_and_bib(
            user["token"], form["event_id"], bib
        )
        latest_result: dict = {}
        for time_event in time_events:
            if (time_event["timing_point"] == "Finish") and (time_event["bib"] == bib):
                if (not latest_result) or (
                    time_event["registration_time"] > latest_result["registration_time"]
                ):
                    latest_result = time_event
        if latest_result:
            latest_result["next_race_id"] = new_race["id"]
            if new_race["round"] == "F":
                latest_result["next_race"] = f"{new_race['round']}{new_race['index']}"
            else:
                latest_result["next_race"] = (
                    f"{new_race['round']}{new_race['index']}{new_race['heat']}"
                )
            latest_result["next_race_position"] = new_start["starting_position"]
            await TimeEventsAdapter().update_time_event(
                user["token"], latest_result["id"], latest_result
            )
            informasjon += " Oppdatert videre til fra forrige runde."
    else:
        informasjon = f"Error. Fant ikke deltaker med startnr {form['bib']}."
    return informasjon


async def get_new_race_info(user: dict, form: dict) -> dict:
    """Extract start pos from form or get best available."""
    startlist_id = ""
    try:
        starting_position = int(form["starting_position"])
        startlist_id = form["startlist_id"]
        start_time = form["start_time"]
        race_id = form["race_id"]
    except Exception:
        starting_position = 1
        race_id = form["new_heat"]
        new_race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
        start_entries = new_race["start_entries"]
        start_time = new_race["start_time"]
        if len(start_entries) > 0:
            startlist_id = start_entries[0]["startlist_id"]
            start_positions_taken = []
            for start_entry in start_entries:
                start_positions_taken.append(start_entry["starting_position"])
            starting_position = max(start_positions_taken) + 1
            for i in range(1, len(start_entries) + 1):
                if i not in start_positions_taken:
                    starting_position = i
                    break
    return {
        "race_id": race_id,
        "starting_position": starting_position,
        "startlist_id": startlist_id,
        "start_time": start_time,
    }


async def delete_start(user: dict, form: dict) -> str:
    """Extract form data and delete one start event."""
    await StartAdapter().delete_start_entry(
        user["token"], form["race_id"], form["start_id"]
    )
    return "Slettet start."


def get_foto_finish_for_race(race: dict, photos: list) -> list:
    """Loop throgh photos and return relevant finish photo(s)."""
    fotos = []
    for photo in photos:
        if photo["race_id"] == race["id"]:
            if photo["is_photo_finish"] and (photo["confidence"] > 80):
                fotos.append(photo)
    return fotos


async def get_race_kpis(
    token: str, event: dict, raceclasses: list, valgt_runde: str
) -> list:
    """Generate a summary with key performance indicators for race execution."""
    summary_kpis = []
    all_races = await RaceplansAdapter().get_all_races(token, event["id"])
    raceplan_summary = get_raceplan_summary(all_races, raceclasses)

    # enrich with race details
    for raceclass in raceplan_summary:
        races = await RaceplansAdapter().get_races_by_racesclass(
            token, event["id"], raceclass["name"]
        )
        races_q = []
        races_s = []
        races_f = []
        for race in races:
            # calculate key kpis pr race
            race_summary = get_race_summary(event, race)

            if (race["round"] in ["Q", "R1"]) and (valgt_runde in ["Q", "A"]):
                races_q.append(race_summary)
            elif (race["round"] in ["S", "R2"]) and (valgt_runde in ["S", "A"]):
                races_s.append(race_summary)
            elif (race["round"] == "F") and (valgt_runde in ["F", "A"]):
                races_f.append(race_summary)
        raceclass["races_q"] = races_q
        raceclass["races_s"] = races_s
        raceclass["races_f"] = races_f
        raceclass["progress"] = get_raceclass_progress(races_q, races_s, races_f)

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
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    for race in races_s:
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    for race in races_q:
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    return raceclass_progress


def get_race_summary(event: dict, race: dict) -> dict:
    """Calculate key kpis for a single race."""
    try:
        count_starts = len(race["start_entries"])
    except Exception:
        count_starts = 0
    try:
        count_results = len(race["results"]["Finish"]["ranking_sequence"])
    except Exception:
        count_results = 0
    try:
        count_dns = len(race["results"]["DNS"]["ranking_sequence"])
    except Exception:
        count_dns = 0
    try:
        count_dnf = len(race["results"]["DNF"]["ranking_sequence"])
    except Exception:
        count_dnf = 0

    race_progress = get_race_progress(
        event, race, count_starts, count_dns, count_dnf, count_results
    )

    if event["competition_format"] != "Individual Sprint":
        race_name = event["competition_format"]
    elif race["round"] == "F":
        race_name = f"{race['round']}{race['index']}"
    else:
        race_name = f"{race['round']}{race['index']}{race['heat']}"

    return {
        "name": race_name,
        "order": race["order"],
        "count_starts": count_starts,
        "count_results": count_results,
        "count_dns": count_dns,
        "count_dnf": count_dnf,
        "progress": race_progress,
        "start_time": race["start_time"][-8:],
    }


def get_race_progress(
    event: dict,
    race: dict,
    count_starts: int,
    count_dns: int,
    count_dnf: int,
    count_results: int,
) -> int:
    """Evaluate race progress and return a code to indicate coloring in dashboard."""
    progress = 6
    # 0 empty / no starts
    # 1 not started
    # 2 not started - with DNS */
    # 3 started - no results */
    # 4 partial results - with DNF */
    # 5 all results ok */
    # 6 error in race results */
    time_now = EventsAdapter().get_local_time(event, "log")
    start_time = race["start_time"]
    if count_starts == 0:
        progress = 0
    elif start_time > time_now:
        if count_results > 0 or count_dnf > 0:
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
