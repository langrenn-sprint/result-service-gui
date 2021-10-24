"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import (
    ContestantsAdapter,
    EventsAdapter,
    StartAdapter,
    TimeEventsAdapter,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check loging and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {"name": session["username"], "token": session["token"]}


async def create_time_event(token: str, action: str, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    reg_time = datetime.datetime.now()

    request_body = {
        "bib": form["bib"],
        "event_id": form["event_id"],
        "race_id": "",
        "point": "",
        "rank": "",
        "registration_time": reg_time.strftime("%X"),
        "next_race_id": "",
        "status": "OK",
        "changelog": "",
    }
    i = 0
    if action == "start_bib":
        # register start
        request_body["point"] = "Start"
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            if bib.count("x") > 0:
                request_body["rank"] = "DNS"
                request_body[
                    "changelog"
                ] = f"{reg_time.strftime('%X')}: DNS registrert. "
                request_body["bib"] = bib.replace("x", "")
            else:
                request_body["rank"] = "Started"
                request_body[
                    "changelog"
                ] = f"{reg_time.strftime('%X')}: Start registrert. "
                request_body["bib"] = bib
            i += 1
            id = await TimeEventsAdapter().create_time_event(token, request_body)
            informasjon += f"{i}. Bib:{bib}. "
    elif action == "start_check":
        for x in form.keys():
            if x.startswith("start_"):
                request_body["bib"] = x[6:]
                request_body["point"] = "Start"
                if form[x] == "DNS":
                    # register DNS
                    request_body["rank"] = "DNS"
                    request_body[
                        "changelog"
                    ] = f"{reg_time.strftime('%X')}: DNS registrert. "
                else:
                    # register normal start
                    request_body["rank"] = "Started"
                    request_body[
                        "changelog"
                    ] = f"{reg_time.strftime('%X')}: Start registrert. "
                i += 1
                id = await TimeEventsAdapter().create_time_event(token, request_body)
                informasjon += f"{i}. Bib:{form['bib']} "
        informasjon = f"Registreringer OK: {i}." + informasjon
    elif action == "finish_bib":
        request_body["point"] = "Finish"
        request_body[
            "changelog"
        ] = f"{reg_time.strftime('%X')}: Målpassering registrert. "
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            request_body["bib"] = bib
            i += 1
            id = await TimeEventsAdapter().create_time_event(token, request_body)
            informasjon += f"{i}. Bib:{bib} "
    elif action == "finish_place":
        logging.info("finish_place")
    logging.debug(f"Registrations: {informasjon}, last id: {id}")

    return f"Registreringer: {i} - {informasjon}"


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

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
    logging.debug(f"Regel hele: {text}")
    return text


async def get_enchiced_startlist(token: str, event_id: str, valgt_klasse: str) -> list:
    """Enrich startlist information."""
    startlist = await StartAdapter().get_all_starts(token, event_id)

    # add name and club
    contestants = await ContestantsAdapter().get_all_contestants(token, event_id, "")
    for start in startlist:
        for contestant in contestants:
            if start["bib"] == str(contestant["bib"]):
                start["name"] = f"{contestant['first_name']} {contestant['last_name']}"
                start["club"] = contestant["club"]
    return startlist


async def update_time_event(token: str, action: str, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    reg_time = datetime.datetime.now()
    request_body = await TimeEventsAdapter().get_time_event_by_id(token, form["id"])
    if "update" in form.keys():
        request_body[
            "changelog"
        ] += f"{reg_time.strftime('%X')}: Oppdatering - tidligere informasjon: {request_body}. "
        request_body["point"] = form["point"]
        request_body["registration_time"] = form["registration_time"]
        request_body["rank"] = form["rank"]
    elif "delete" in form.keys():
        request_body[
            "changelog"
        ] += f"{reg_time.strftime('%X')}: Status set to deleted "
        request_body["status"] = "Deleted"
    informasjon = await TimeEventsAdapter().update_time_event(
        token, form["id"], request_body
    )
    logging.debug(f"Control result: {informasjon}")

    return f"Control result: <br>{informasjon}"
