"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import EventsAdapter, TimeEventsAdapter, UserAdapter


async def check_login(self) -> dict:
    """Check loging and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {"name": session["username"], "token": session["token"]}


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event


async def create_time_event(token: str, mode: str, input_data: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    reg_time = datetime.datetime.now()
    request_body = {
        "bib": input_data["bib"],
        "event_id": input_data["event_id"],
        "race_id": "",
        "point": "",
        "registration_time": reg_time.strftime("%X"),
        "next_race_id": "",
        "status": "OK",
        "changelog": "",
    }
    if mode == "start_bib":
        request_body["point"] = "Start"
        id = await TimeEventsAdapter().create_time_event(token, request_body)
        informasjon = f"Registrering OK. Input data: {input_data}, med id: {id}"
    elif mode == "start_check":
        for x in input_data.keys():
            logging.info(f"Key {x}: {input_data[x]}")
            if x.startswith("start_"):
                request_body["bib"] = x[6:]
                if input_data[x] == "DNS":
                    # register DNS
                    request_body["point"] = input_data[x]
                    request_body["changelog"] = "DNS registered at start"
                    id = await TimeEventsAdapter().create_time_event(
                        token, request_body
                    )
                    informasjon += (
                        f"Registrering OK. Input data: {input_data}, med id: {id}"
                    )
                elif input_data[x] == "OK":
                    # register start
                    request_body["point"] = "Start"
                    id = await TimeEventsAdapter().create_time_event(
                        token, request_body
                    )
                    informasjon += (
                        f"Registrering OK. Input data: {input_data}, med id: {id}"
                    )
    elif mode == "finish_bib":
        request_body["point"] = "Finish"
        id = await TimeEventsAdapter().create_time_event(token, request_body)
        informasjon = f"Registrering OK. Input data: {input_data}, med id: {id}"
    elif mode == "finish_place":
        logging.info("finish_place")
    elif mode == "control":
        logging.info("control")

    return informasjon
