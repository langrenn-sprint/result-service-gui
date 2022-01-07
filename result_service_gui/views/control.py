"""Resource module for control resources."""
import datetime
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    get_event,
    get_passeringer,
    get_race_id_by_name,
    update_time_event,
)


class Control(web.View):
    """Class representing the control view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        event_id = self.request.rel_url.query["event_id"]
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
            informasjon = f"Velg funksjon. {informasjon}"
        try:
            valgt_klasse = self.request.rel_url.query["valgt_klasse"]
        except Exception:
            valgt_klasse = ""

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # get passeringer
            passeringer = await get_passeringer(user["token"], event_id, action, "")

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "control.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "username": user["name"],
                    "valgt_klasse": valgt_klasse,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            valgt_klasse = str(form["valgt_klasse"])
            action = str(form["action"])
            if "update_templates" in form.keys():
                informasjon = await update_template_events(user, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/control?event_id={event_id}&informasjon={informasjon}&action={action}&valgt_klasse={valgt_klasse}"
        )


async def update_template_events(user: dict, form: dict) -> str:
    """Extract form data and update time events in one heat."""
    informasjon = "Control result: "
    for i in range(1, 11):
        if f"next_race_{i}" in form.keys():
            if form[f"next_race_{i}"]:
                request_body = {
                    "event_id": form["event_id"],
                    "id": form[f"id_{i}"],
                    "update_template": True,
                    "next_race": form[f"next_race_{i}"],
                    "next_race_position": form[f"next_race_position_{i}"],
                    "race": form["race"],
                }
                informasjon += await update_time_event(user, request_body)
    if form["rank_new"]:
        next_race_id = await get_race_id_by_name(
            user, form["event_id"], form["next_race_new"], form["valgt_klasse"]
        )
        time_now = datetime.datetime.now()
        time_event = {
            "bib": 0,
            "event_id": form["event_id"],
            "race": form["race"],
            "race_id": form["race_id"],
            "timing_point": "Template",
            "rank": form["rank_new"],
            "registration_time": time_now.strftime("%X"),
            "next_race": form["next_race_new"],
            "next_race_id": next_race_id,
            "next_race_position": form["next_race_position_new"],
            "status": "OK",
            "changelog": [],
        }
        id = await TimeEventsAdapter().create_time_event(user["token"], time_event)
        informasjon += f" Added new {id} "
    return informasjon
