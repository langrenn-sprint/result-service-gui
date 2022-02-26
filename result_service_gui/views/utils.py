"""Utilities module for gui services."""
import datetime
import json
import logging
import os

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import (
    EventsAdapter,
    RaceplansAdapter,
    ResultAdapter,
    StartAdapter,
    TimeEventsAdapter,
    TimeEventsService,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check loging and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")  # type: ignore

    return {"name": session["username"], "token": session["token"]}


async def check_login_open(self) -> dict:
    """Check loging and return user credentials."""
    user = {}
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if loggedin:
        user = {
            "name": session["username"],
            "loggedin": True,
            "token": session["token"],
        }
    else:
        user = {"name": "Gjest", "loggedin": False, "token": ""}

    return user


async def create_finish_time_events(user: dict, action: str, form: dict) -> list:
    """Register time events for finish- return information."""
    informasjon = []
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"

    request_body = {
        "id": "",
        "bib": 0,
        "event_id": form["event_id"],
        "race": form["race"],
        "race_id": form["race_id"],
        "timing_point": "",
        "rank": "",
        "registration_time": time_stamp_now,
        "next_race": "",
        "next_race_id": "",
        "next_race_position": 0,
        "status": "OK",
        "changelog": [],
    }
    i = 0
    if "finish" in form.keys():
        request_body["timing_point"] = "Finish"
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": "Målpassering registrert. ",
            }
        ]
        biblist = form["bib"].rsplit(" ")
        informasjon.append("Målpassering registrert: ")
        for bib in biblist:
            request_body["bib"] = int(bib)
            i += 1
            id = await TimeEventsService().create_finish_time_event(
                user["token"], request_body
            )
            informasjon.append(f" {bib}, result: {id} ")
            logging.debug(f"Registrering: {id} - body: {request_body}")
    elif action == "finish_bib":
        request_body["timing_point"] = "Finish"
        new_registrations = []
        for x in form.keys():
            bib_changed = True
            if x.startswith("form_rank_"):
                new_bib = form[x]
                _rank = int(x[10:])
                # check if anything is changed and delete old registration
                if form[f"old_form_rank_{_rank}"]:
                    old_bib = form[f"old_form_rank_{_rank}"]
                    if old_bib == new_bib:
                        bib_changed = False
                    else:
                        new_form = {
                            "time_event_id": form[f"time_event_id_{_rank}"],
                        }
                        info = await delete_result(user, new_form)
                        informasjon.append(info)
                        logging.debug(f"Deleted result: {informasjon}")
                if new_bib.isnumeric() and bib_changed:
                    new_entry = {
                        "id": "",
                        "bib": int(new_bib),
                        "event_id": request_body["event_id"],
                        "race": request_body["race"],
                        "race_id": request_body["race_id"],
                        "timing_point": request_body["timing_point"],
                        "rank": _rank,
                        "registration_time": time_stamp_now,
                        "next_race": "",
                        "next_race_id": "",
                        "next_race_position": 0,
                        "status": "OK",
                        "changelog": [
                            {
                                "timestamp": time_stamp_now,
                                "user_id": user["name"],
                                "comment": f"{request_body['rank']} plass i mål. ",
                            }
                        ],
                    }
                    i += 1
                    new_registrations.append(new_entry)
        # register new results
        for new_registration in new_registrations:
            id = await TimeEventsService().create_finish_time_event(
                user["token"], new_registration
            )
            informasjon.append(f" {id} ")
            logging.debug(f"Registrering: {id} - body: {new_registration}")

    informasjon.append(f"Utført {i} registreringer.")
    return informasjon


async def create_start_time_events(user: dict, form: dict) -> str:
    """Extract form data and create time_events for start."""
    informasjon = ""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"

    request_body = {
        "id": "",
        "bib": 0,
        "event_id": form["event_id"],
        "race": form["race"],
        "race_id": form["race_id"],
        "timing_point": "",
        "rank": "",
        "registration_time": time_now.strftime("%X"),
        "next_race": "",
        "next_race_id": "",
        "next_race_position": 0,
        "status": "OK",
        "changelog": [],
    }
    i = 0
    informasjon = ""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"

    if "bib" in form.keys():
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            if bib.count("x") > 0:
                request_body["timing_point"] = "DNS"
                changelog_comment = "DNS registrert. "
                request_body["bib"] = int(bib.replace("x", ""))
            else:
                request_body["timing_point"] = "Start"
                changelog_comment = "Start registrert. "
                request_body["bib"] = int(bib)
            i += 1
            request_body["changelog"] = [
                {
                    "timestamp": time_stamp_now,
                    "user_id": user["name"],
                    "comment": changelog_comment,
                }
            ]
            id = await TimeEventsService().create_start_time_event(
                user["token"], request_body
            )
            informasjon += f" {request_body['bib']}-{changelog_comment}. "
            logging.debug(f"Registrering: {id} - body: {request_body}")
    else:
        for x in form.keys():
            if x.startswith("form_start_"):
                request_body["bib"] = int(x[11:])
                if form[x] == "DNS":
                    # register DNS
                    request_body["timing_point"] = "DNS"
                    changelog_comment = "DNS registrert. "
                else:
                    # register normal start
                    request_body["timing_point"] = "Start"
                    changelog_comment = "Start registrert. "
                i += 1
                request_body["changelog"] = [
                    {
                        "timestamp": time_stamp_now,
                        "user_id": user["name"],
                        "comment": changelog_comment,
                    }
                ]
                id = await TimeEventsService().create_start_time_event(
                    user["token"], request_body
                )
                informasjon += f" {request_body['bib']}-{changelog_comment}. "
                logging.debug(f"Registrering: {id} - body: {request_body}")
    return informasjon


async def delete_result(user: dict, form: dict) -> str:
    """Set time event to deleted and delete corresponding start event."""
    informasjon = ""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"

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
                informasjon = f"Slettet start entry i neste heat. Resultat: {id}"
    time_event["status"] = "Deleted"
    change_info = {
        "timestamp": time_stamp_now,
        "user_id": user["name"],
        "comment": f"Error - resultat slettet. Bib {time_event['bib']}",
    }
    time_event["changelog"].append(change_info)
    id2 = await TimeEventsAdapter().update_time_event(
        user["token"], form["time_event_id"], time_event
    )
    informasjon = f"Registrert slettet målpassering. Resultat: {id2}  {informasjon}"
    return informasjon


def get_display_style(start_time: str) -> str:
    """Calculate time remaining to start and return table header style."""
    start_time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
    delta_time = start_time_obj - datetime.datetime.now()
    delta_seconds = delta_time.total_seconds()
    display_style = ""
    if delta_seconds < 240:
        display_style = "table_header_red"
    elif delta_seconds < 480:
        display_style = "table_header_orange"
    else:
        display_style = "table_header_green"

    return display_style


async def get_enchiced_startlist(user: dict, race_id: str) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    i = 0
    # get time-events registered
    next_race_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race_id
    )
    race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
    new_start_entries = race["start_entries"]
    if len(new_start_entries) > 0:
        for start_entry in new_start_entries:
            i += 1
            for time_event in next_race_time_events:
                # get next race info
                if time_event["timing_point"] == "Template":
                    if i == time_event["rank"]:
                        if time_event["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry["next_race"] = time_event["next_race"]
                # check if start or DNS is registered
                elif time_event["timing_point"] == "Start":
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["start_status"] = "Started"
                        start_entry[
                            "info"
                        ] = f"Started registered at {time_event['registration_time']}"
                elif time_event["timing_point"] == "DNS":
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["start_status"] = "DNS"
                        start_entry[
                            "info"
                        ] = f"DNS registered at {time_event['registration_time']}"
            startlist.append(start_entry)

    return startlist


async def get_finish_timings(user: dict, race_id: str) -> list:
    """Get finish events for race, Template event if no result is registered."""
    finish_events = []
    # get time-events registered
    time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race_id
    )
    for i in range(1, 11):
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
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(user["token"], event_id)

    return event


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
                        if rank_event["status"] == "OK":
                            finish_rank.append(rank_event)
    return finish_rank


def get_global_parameter(param_name: str) -> str:
    """Get global settings from parameter file."""
    photo_settings = str(os.getenv("GLOBAL_SETTINGS_FILE"))
    if photo_settings is None or photo_settings == "None":
        raise web.HTTPBadRequest(
            reason="Parameter GLOBAL_SETTINGS_FILE not found in docker-compose.yaml file."
        )
    with open(photo_settings) as json_file:
        photopusher_settings = json.load(json_file)
    return photopusher_settings[param_name]


def get_local_time(format: str) -> str:
    """Return local time, time zone adjusted from settings file."""
    TIME_ZONE_OFFSET = os.getenv("TIME_ZONE_OFFSET")
    # calculate new time
    delta_seconds = int(TIME_ZONE_OFFSET) * 3600  # type: ignore
    local_time_obj = datetime.datetime.now() + datetime.timedelta(seconds=delta_seconds)
    local_time = ""
    if format == "HH:MM":
        local_time = f"{local_time_obj.strftime('%H')}:{local_time_obj.strftime('%M')}"
    else:
        local_time = local_time_obj.strftime("%X")
    return local_time


def get_next_race_info(next_race_time_events: list, race_id: str) -> list:
    """Enrich start list with next race info."""
    startlist = []
    # get videre til information - loop and simulate result for pos 1 to 8
    for x in range(1, 9):
        for template in next_race_time_events:
            start_entry = {}
            _rank = template["rank"]
            if template["timing_point"] == "Template":
                if _rank == x:
                    start_entry["race_id"] = race_id
                    start_entry["starting_position"] = x  # type: ignore
                    if template["next_race"].startswith("Ute"):
                        start_entry["next_race"] = "Ute"
                    else:
                        start_entry["next_race"] = template["next_race"]
                    startlist.append(start_entry)
    return startlist


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
                    if x == "A" and y > 0:
                        text += f"{y} til semi A. "
                    elif x == "C" and y > 0:
                        text += "Resten til semi C. "
            elif key == "F":
                for x, y in value.items():
                    if x == "A":
                        text += f"{y} til finale A. "
                    elif x == "B" and y > 8:
                        text += "Resten til finale B. "
                    elif x == "B":
                        text += f"{y} til finale B. "
                    elif x == "C" and y > 8:
                        text += "Resten til finale C. "
                    elif x == "C":
                        text += f"{y} til finale C. "
                if text.count("Resten") == 0:
                    text += "Resten er ute. "
    logging.debug(f"Regel hele: {text}")
    return text


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


def get_races_for_live_view(races, valgt_heat: int, number_of_races: int) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    time_now = get_local_time("HH:MM:SS")
    i = 0
    # find next race on start
    if valgt_heat == 0:
        for race in races:
            if time_now < race["start_time"][-8:]:
                valgt_heat = race["order"]
                break

    for race in races:
        # from heat number (order) if selected
        if (race["order"] >= valgt_heat) and (i < number_of_races):
            race["next_race"] = get_qualification_text(race)
            race["display_color"] = get_display_style(race["start_time"])
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
                    race["first_in_class"] = first_in_class
                    race["next_race"] = get_qualification_text(race)
                    race["start_time"] = race["start_time"][-8:]
                    # get start list details
                    if (
                        action == "start" or len(race["results"]) == 0
                    ) and action != "result":
                        race["list_type"] = "start"
                        race["startliste"] = await get_enchiced_startlist(
                            user, race["id"]
                        )
                    else:
                        race["list_type"] = action
                        race_details = await RaceplansAdapter().get_race_by_id(
                            user["token"], race["id"]
                        )
                        race["finish_results"] = get_finish_rank(race_details)
                    if first_in_class:
                        first_in_class = False
                    races.append(race)
    return races


async def get_races_for_round_result(
    user: dict, _tmp_races: list, valgt_runde: str, valgt_klasse: str
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
            race["start_time"] = race["start_time"][-8:]
            if race["round"] == valgt_runde:
                race["first_in_class"] = first_in_class
                first_in_class = False
                race["next_race"] = get_qualification_text(race)
                race["list_type"] = "result"
                race_details = await RaceplansAdapter().get_race_by_id(
                    user["token"], race["id"]
                )
                race["finish_results"] = get_finish_rank(race_details)
                races.append(race)
            elif race["round"] in next_round:
                race["first_in_class"] = first_in_next_round
                first_in_next_round = False
                race["next_race"] = get_qualification_text(race)
                race["list_type"] = "start"
                race["startliste"] = await get_enchiced_startlist(user, race["id"])
                races.append(race)
    return races


async def get_results_by_raceclass(
    user: dict, event_id: str, valgt_klasse: str
) -> list:
    """Get results for raceclass - return sorted list."""
    results = []
    grouped_results = {  # type: ignore
        "FA": [],
        "FB": [],
        "SA": [],
        "FC": [],
        "SC": [],
    }
    races = await RaceplansAdapter().get_races_by_racesclass(
        user["token"], event_id, valgt_klasse
    )
    # first - extract all result-items
    for race in races:
        if len(race["results"]) == 0:
            # need results for all races - exit if not
            return []
        # skip results from qualification
        if race["round"] != "Q":
            _tmp_results = await ResultAdapter().get_race_results(
                user["token"], race["id"]
            )
            for _tmp_result in _tmp_results[0]["ranking_sequence"]:
                # skip results if racer has more races
                if _tmp_result["next_race_id"] == "" and _tmp_result["status"] == "OK":
                    new_result: dict = {
                        "round": f"{race['round']}{race['index']}",
                        "rank": 0,
                        "time_event": _tmp_result,
                    }
                    grouped_results[f"{race['round']}{race['index']}"].append(
                        new_result
                    )

    # now - get the order and rank right
    ranking = 1
    racers_count = 0
    for round_res in grouped_results:
        for one_res in grouped_results[round_res]:
            one_res["rank"] = ranking
            results.append(one_res)
            racers_count += 1
            if one_res["round"].startswith("F"):
                ranking += 1
        else:
            ranking = racers_count + 1

    return results


async def update_time_event(user: dict, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"
    request_body = await TimeEventsAdapter().get_time_event_by_id(
        user["token"], form["id"]
    )
    if "update" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": f"Oppdatering - tidligere informasjon: {request_body}. ",
            }
        ]
        request_body["timing_point"] = form["timing_point"]
        request_body["registration_time"] = form["registration_time"]
        request_body["rank"] = form["rank"]
    elif "update_template" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": f"Oppdatering - old info, next_race {request_body['next_race']}-{request_body['next_race_position']}. ",
            }
        ]
        request_body["next_race_position"] = form["next_race_position"]
        raceclass = form["race"].split("-")
        request_body["next_race_id"] = await get_race_id_by_name(
            user, form["event_id"], form["next_race"], raceclass[0]
        )
        request_body["next_race"] = form["next_race"]
    elif "delete" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["name"],
                "comment": "Status set to deleted . ",
            }
        ]
        request_body["status"] = "Deleted"
    response = await TimeEventsAdapter().update_time_event(
        user["token"], form["id"], request_body
    )
    logging.debug(f"Control result: {response}")
    informasjon = f"Oppdatert - {response}  "
    return informasjon


async def get_race_id_by_name(
    user: dict, event_id: str, next_race: str, raceclass: str
) -> str:
    """Get race_id for a given race."""
    race_id = ""
    races = await RaceplansAdapter().get_all_races(user["token"], event_id)
    for race in races:
        if race["raceclass"] == raceclass:
            tmp_next_race = f"{race['round']}{race['index']}{race['heat']}"
            if next_race == tmp_next_race:
                return race["id"]
    return race_id


async def get_passeringer(
    token: str, event_id: str, action: str, valgt_klasse: str
) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
        token, event_id
    )
    if action in [
        "control",
        "deleted",
    ]:
        for passering in reversed(tmp_passeringer):
            if valgt_klasse == "" or valgt_klasse in passering["race"]:
                if (
                    passering["status"] == "Error"
                    and passering["timing_point"] != "Template"
                    and action == "control"
                ):
                    passeringer.append(passering)
                elif passering["status"] == "Deleted" and action == "deleted":
                    passeringer.append(passering)
    elif action in [
        "Template",
    ]:
        for passering in tmp_passeringer:
            if valgt_klasse in passering["race"]:
                if passering["timing_point"] == "Template":
                    passeringer.append(passering)
    else:
        for passering in tmp_passeringer:
            if passering["timing_point"] not in [
                "Template",
                "Error",
                "Deleted",
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

    return passeringer
