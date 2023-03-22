"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session, new_session

from result_service_gui.services import (
    EventsAdapter,
    GooglePhotosAdapter,
    RaceclassResultsService,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    TimeEventsService,
    UserAdapter,
)


async def get_auth_url_google_photos(self, redirect_url: str, event_id: str) -> str:
    """Check authorization for google photos and return url - blank if authorized."""
    session = await get_session(self.request)
    authorized = UserAdapter().isloggedin_google_photos(session)
    if not authorized:
        authorization_request_url = await GooglePhotosAdapter().get_auth_request_url(
            redirect_url, event_id
        )
    else:
        authorization_request_url = ""
    return authorization_request_url


async def login_google_photos(
    self, redirect_url: str, event_id: str, user: dict
) -> int:
    """Check scope authorization for google photos and store in session."""
    session = await new_session(self.request)
    result = UserAdapter().login_google_photos(redirect_url, event_id, user, session)
    return result


async def check_login(self) -> dict:
    """Check login and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        raise web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")  # type: ignore

    return {
        "name": session["name"],
        "loggedin": True,
        "token": session["token"],
        "g_loggedin": session["g_loggedin"],
        "g_name": session["g_name"],
        "g_jwt": session["g_jwt"],
        "g_auth_photos": session["g_auth_photos"],
        "g_scope": session["g_scope"],
        "g_client_id": session["g_client_id"],
        "g_photos_token": session["g_photos_token"],
    }


async def check_login_google(self, event_id: str) -> dict:
    """Check login with google and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin_google(session)
    if not loggedin:
        informasjon = "informasjon=Logg inn med google for å se denne siden."
        info = f"action=g_login&event_id={event_id}"
        raise Exception(f"/login?{info}&{informasjon}")

    return {
        "name": session["name"],
        "loggedin": loggedin,
        "token": session["token"],
        "g_loggedin": session["g_loggedin"],
        "g_name": session["g_name"],
        "g_jwt": session["g_jwt"],
        "g_auth_photos": session["g_auth_photos"],
        "g_scope": session["g_scope"],
        "g_client_id": session["g_client_id"],
        "g_photos_token": session["g_photos_token"],
    }


async def check_login_google_photos(self, event_id: str) -> dict:
    """Check login with google and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin_google_photos(session)
    if not loggedin:
        informasjon = "informasjon=Logg inn med google for å se denne siden."
        info = f"action=g_login&event_id={event_id}"
        raise Exception(f"/login?{info}&{informasjon}")

    return {
        "name": session["name"],
        "loggedin": loggedin,
        "token": session["token"],
        "g_loggedin": session["g_loggedin"],
        "g_name": session["g_name"],
        "g_jwt": session["g_jwt"],
        "g_auth_photos": session["g_auth_photos"],
        "g_scope": session["g_scope"],
        "g_client_id": session["g_client_id"],
        "g_photos_token": session["g_photos_token"],
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


async def delete_result(user: dict, form: dict) -> str:
    """Set time event to deleted and delete corresponding start event."""
    informasjon = ""

    # get time event and delete next start if existing
    time_event = await TimeEventsAdapter().get_time_event_by_id(
        user["token"], form["time_event_id"]
    )
    if len(time_event["next_race_id"]) > 0:
        start_entries = await StartAdapter().get_start_entries_by_race_id(
            user["token"], time_event["next_race_id"]
        )
        for start_entry in start_entries:
            if time_event["bib"] == start_entry["bib"]:
                id = await StartAdapter().delete_start_entry(
                    user["token"], start_entry["race_id"], start_entry["id"]
                )
                informasjon = f"Slettet neste start ({time_event['bib']}). "
                logging.debug(f"Deleted start - result {id}")
    id2 = await TimeEventsAdapter().delete_time_event(
        user["token"], form["time_event_id"]
    )
    logging.debug(f"Time event deleted: {id2} - {form['time_event_id']}")
    informasjon = f"Slettet passering ({time_event['bib']}). {informasjon}"
    return informasjon


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
        display_style = "table_header_red"
    elif delta_seconds < 600:
        display_style = "table_header_orange"
    else:
        display_style = "table_header_green"

    return display_style


async def get_enrichced_startlist(user: dict, race: dict) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    i = 0
    # get time-events registered
    next_race_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race["id"]
    )
    new_start_entries = race["start_entries"]
    if len(new_start_entries) > 0:
        for start_entry in new_start_entries:
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
    for i in range(1, race['max_no_of_contestants'] + 1):
        bfound_event = False
        for time_event in time_events:
            if time_event["timing_point"] == "Finish" and time_event["status"] == "OK":
                if i == time_event["rank"]:
                    bfound_event = True
                    finish_events.append(time_event)
                    break
        if (not bfound_event) and (i < 11):
            for time_event in time_events:
                if (time_event["timing_point"] == "Template") and (
                    i == time_event["rank"]
                ):
                    bfound_event = True
                    finish_events.append(time_event)
                    break
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
        if passering['race'].startswith(valgt_klasse):
            tmp_passeringer.append(passering)

    if action == "control":
        for passering in reversed(tmp_passeringer):
            if not valgt_klasse or valgt_klasse in passering["race"]:
                if (
                    passering["status"] == "Error"
                    and passering["timing_point"] != "Template"
                ):
                    passeringer.append(passering)
    elif action in [
        "Template", "DNS"
    ]:
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
    def myfunc(n):
        return n['registration_time']
    passeringer.sort(key = myfunc )
    passeringer.reverse()

    return passeringer


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] == "R2":
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
    races = await RaceplansAdapter().get_races_by_racesclass(user["token"], event_id, raceclass)
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
                if race["datatype"] == "individual_sprint":
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


def get_races_for_live_view(event: dict, races: list, valgt_heat: int, number_of_races: int) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    i = 0
    time_now = EventsAdapter().get_local_time(
        event, "log"
    )
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
    for raceclass in raceclasses:
        first_in_class = True
        for race in _tmp_races:
            if race["raceclass"] == raceclass["name"]:
                if (race["raceclass"] == valgt_klasse) or ("" == valgt_klasse):
                    race = await RaceplansAdapter().get_race_by_id(
                        user["token"], race["id"]
                    )
                    race["first_in_class"] = first_in_class
                    race["next_race"] = get_qualification_text(race)
                    race["start_time"] = race["start_time"][-8:]
                    # get start list details
                    if (action == "live"):
                        race["list_type"] = "start"
                        if race['results']:
                            if "Finish" in race['results'].keys():  # type: ignore
                                race["list_type"] = "result"
                    else:
                        race["list_type"] = action

                    if (race["list_type"] == "start"):
                        race["startliste"] = await get_enrichced_startlist(user, race)
                    else:
                        race[
                            "finish_results"
                        ] = RaceclassResultsService().get_finish_rank_for_race(race, False)
                    if first_in_class:
                        first_in_class = False
                    races.append(race)
    return races


async def get_races_for_round_result(
    user: dict, _tmp_races: list, valgt_runde: str, valgt_klasse: str, action: str
) -> list:
    """Get races for a given round - formatted for print."""
    races = []
    next_round = []
    first_in_class = True
    first_in_next_round = True
    if valgt_runde == "Q":
        next_round = ["S", "F"]
    elif valgt_runde == "S":
        next_round = ["F"]

    for race in _tmp_races:
        if race["raceclass"] == valgt_klasse:
            race = await RaceplansAdapter().get_race_by_id(user["token"], race["id"])
            race["start_time"] = race["start_time"][-8:]
            if race["round"] == valgt_runde:
                if action.count("result") > 0:
                    race["first_in_class"] = first_in_class
                    first_in_class = False
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "result"
                    race[
                        "finish_results"
                    ] = RaceclassResultsService().get_finish_rank_for_race(race, False)
                    races.append(race)
            elif race["round"] in next_round:
                if action.count("start") > 0:
                    race["first_in_class"] = first_in_next_round
                    first_in_next_round = False
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "start"
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    races.append(race)
    return races


async def update_finish_time_events(
    user: dict, delete_result_list: list, add_result_list: list
) -> str:
    """Update time events for finish- return information."""
    informasjon = ""
    for del_result in delete_result_list:
        info = await delete_result(user, del_result)
        informasjon += info
        logging.debug(f"Deleted result: {info} - body: {del_result}")

    info = await TimeEventsService().create_finish_time_events(
        user["token"], add_result_list
    )
    informasjon += info
    logging.debug(f"Registreringer: {info} - body: {add_result_list}")
    return informasjon
