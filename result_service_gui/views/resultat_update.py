"""Resource module for single result update via ajax."""
import logging

from aiohttp import web

from result_service_gui.services import (
    EventsAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login, get_event
)


class ResultatUpdate(web.View):
    """Class representing the simple photo update service."""

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        result = ""
        try:
            form = await self.request.post()
            action = form['action']
            user = await check_login(self)
            if action in ["DNF", "DNS", "Start"]:
                result = await create_event(user, form, action)  # type: ignore
        except Exception as e:
            result = f"Det har oppstått en feil: {e}"
            logging.error(f"Result update - {e}")
        return web.Response(text=result)


async def create_event(user: dict, form: dict, action: str) -> str:
    """Extract form data and create one time_event, DNS, DNF or Start."""
    informasjon = ""
    event_id = form["event_id"]
    event = await get_event(user, event_id)
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    if form['checked'] == "true":
        request_body = {
            "id": "",
            "bib": int(form["bib"]),
            "event_id": event_id,
            "race": form["race"],
            "race_id": form["race_id"],
            "timing_point": action,
            "rank": "",
            "registration_time": time_stamp_now,
            "next_race": "",
            "next_race_id": "",
            "next_race_position": 0,
            "status": "OK",
            "changelog": [
                {
                    "timestamp": time_stamp_now,
                    "user_id": user["name"],
                    "comment": f"{action} created",
                }
            ],
        }
        new_t_e = await TimeEventsAdapter().create_time_event(user["token"], request_body)
        informasjon = f" Nr {new_t_e['bib']} - {action} registrert. "
    else:
        informasjon = " DNF må slettes manuelt "

    # delete old entry if existing
    try:
        if form['old_id']:
            await TimeEventsAdapter().delete_time_event(user["token"], form['old_id'])
            informasjon += " Slettet gammel registrering."
    except Exception as e:
        logging.debug(f"Delete failed - ignoring {e}")

    return informasjon
