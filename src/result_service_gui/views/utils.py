"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import (
    EventsAdapter,
    RaceplansAdapter,
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
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {"username": session["username"], "token": session["token"]}


async def create_time_event(user: dict, action: str, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"

    request_body = {
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
    if action == "start":
        # register start
        if p in form.keys():
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
                        "user_id": user["username"],
                        "comment": changelog_comment,
                    }
                ]
                id = await TimeEventsService().create_time_event(
                    user["token"], request_body
                )
                informasjon += f" {request_body['bib']}-{changelog_comment}. "
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
                            "user_id": user["username"],
                            "comment": changelog_comment,
                        }
                    ]
                    id = await TimeEventsService().create_time_event(
                        user["token"], request_body
                    )
                    informasjon += f" {request_body['bib']}-{changelog_comment}. "
    elif action == "finish_bib1":
        request_body["timing_point"] = "Finish"
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["username"],
                "comment": "Målpassering registrert. ",
            }
        ]
        biblist = form["bib"].rsplit(" ")
        informasjon = "Målpassering registrert: "
        for bib in biblist:
            request_body["bib"] = int(bib)
            i += 1
            id = await TimeEventsService().create_time_event(
                user["token"], request_body
            )
            informasjon += f" {bib} "
    elif action == "finish_bib2":
        request_body["timing_point"] = "Finish"
        for x in form.keys():
            if x.startswith("form_place_"):
                _bib = form[x]
                if _bib.isnumeric():
                    request_body["bib"] = int(_bib)
                    request_body["rank"] = x[11:]
                    request_body["changelog"] = [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["username"],
                            "comment": "{request_body['rank']} plass i mål. ",
                        }
                    ]
                    i += 1
                    id = await TimeEventsService().create_time_event(
                        user["token"], request_body
                    )
                    informasjon += (
                        f" {request_body['bib']}-{request_body['rank']} plass. "
                    )
    elif action == "finish_place":
        request_body["timing_point"] = "Finish"
        for x in form.keys():
            if x.startswith("form_place_"):
                _place = form[x]
                if _place.isnumeric():
                    request_body["bib"] = int(x[11:])
                    request_body["rank"] = _place
                    request_body["changelog"] = [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["username"],
                            "comment": f"{request_body['rank']} plass i mål. ",
                        }
                    ]
                    i += 1
                    id = await TimeEventsService().create_time_event(
                        user["token"], request_body
                    )
                    informasjon += (
                        f" {request_body['bib']}-{request_body['rank']} plass. "
                    )
    logging.debug(f"Registrations: {informasjon}, last id: {id}")

    return f"Utført {i} registreringer: {informasjon}"


async def get_enchiced_startlist(user: dict, race_id: str, start_entries: list) -> list:
    """Enrich startlist information."""
    startlist = []
    # get template time-events - for next race
    next_race_templates = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race_id
    )

    if len(start_entries) > 0:
        for start_id in start_entries:
            start_entry = await StartAdapter().get_start_entry_by_id(
                user["token"], race_id, start_id
            )
            for template in next_race_templates:
                if template["timing_point"] == "Template":
                    if template["rank"] == start_entry["starting_position"]:
                        if template["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry[
                                "next_race"
                            ] = f"{template['next_race']}-{template['next_race_position']}"
            startlist.append(start_entry)
    else:
        # get videre til information - loop and simulate result for pos 1 to 8
        for x in range(1, 9):
            for template in next_race_templates:
                start_entry = {}
                if template["timing_point"] == "Template":
                    if int(template["rank"]) == x:
                        start_entry["race_id"] = race_id
                        start_entry["starting_position"] = x
                        if template["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry[
                                "next_race"
                            ] = f"{template['next_race']}-{template['next_race_position']}"
                        startlist.append(start_entry)
    return startlist


async def get_event(user: dict, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(user["token"], event_id)

    return event


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
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
        # loop through races - update start time pr round pr class
        for race in reversed(races):
            if race["raceclass"] == raceclass["name"]:
                if race["datatype"] == "individual_sprint":
                    if race["round"] == "Q":
                        class_summary["timeQ"] = race["start_time"][-8:]
                    elif race["round"] == "S":
                        class_summary["timeS"] = race["start_time"][-8:]
                    elif race["round"] == "F":
                        class_summary["timeF"] = race["start_time"][-8:]
        summary.append(class_summary)
    logging.debug(summary)
    return summary


async def get_races_for_live_view(
    user: dict, event_id: str, valgt_heat: int, number_of_races: int
) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    time_now = datetime.datetime.now().strftime("%X")
    i = 0
    # get races
    races = await RaceplansAdapter().get_all_races(user["token"], event_id)
    for race in races:
        # from heat number (order) if selected
        if (
            (valgt_heat != 0)
            and (race["order"] >= valgt_heat)
            and (i < number_of_races)
        ):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1
        # show upcoming heats from now
        elif (
            (valgt_heat == 0)
            and (time_now < race["start_time"][-8:])
            and (i < number_of_races)
        ):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1

    return filtered_racelist


async def update_time_event(user: dict, action: str, form: dict) -> str:
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
                "user_id": user["username"],
                "comment": "Oppdatering - tidligere informasjon: {request_body}. ",
            }
        ]
        request_body["timing_point"] = form["timing_point"]
        request_body["registration_time"] = form["registration_time"]
        request_body["rank"] = form["rank"]
    elif "delete" in form.keys():
        request_body["changelog"] = [
            {
                "timestamp": time_stamp_now,
                "user_id": user["username"],
                "comment": "Status set to deleted . ",
            }
        ]
        request_body["status"] = "Deleted"
    informasjon = await TimeEventsService().update_time_event(
        user["token"], form["id"], request_body
    )
    logging.debug(f"Control result: {informasjon}")

    return f"Control result: Oppdatert - {informasjon}"
