"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    TimeEventsService,
)
from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
)


class Timing(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
            informasjon = f"Velg funksjon i menyen. {informasjon}"
        try:
            valgt_heat = int(self.request.rel_url.query["heat"])
        except Exception:
            valgt_heat = 0

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            races = []
            if valgt_heat == 0:
                # find race starting now
                all_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
                time_now = EventsAdapter().get_local_time(event, "HH:MM:SS")
                # find next race on start
                valgt_heat = 1
                for tmp_race in all_races:
                    if time_now < tmp_race["start_time"][-8:]:
                        valgt_heat = tmp_race["order"]
                        break
            race = await RaceplansAdapter().get_race_by_order(
                user["token"], event_id, valgt_heat
            )
            races.append(race)
            if len(races) > 0:
                for race in races:
                    # get start and finish list detail
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    race["finish_timings"] = await get_finish_timings(user, race["id"])
            else:
                informasjon = "Fant ingen heat. Velg på nytt."

            # get passeringer
            passeringer = await get_passeringer(user["token"], event_id, action)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "raceclasses": raceclasses,
                    "races": races,
                    "username": user["name"],
                    "valgt_heat": valgt_heat,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that register started or DNS."""
        # check login
        user = await check_login(self)
        informasjon = ""
        try:
            form = await self.request.post()
            event_id = str(form["event_id"])
            event = await get_event(user, event_id)
            action = str(form["action"])
            valgt_heat = str(form["heat"])

            if "finish" in action:
                informasjon = "Funksjon ikke støttet, bruk hovedside for tidtaker"
            elif action == "start":
                informasjon = await create_start_time_events_for_race(user, event, form)  # type: ignore
            elif action == "dns_manual":
                informasjon = await create_dns_time_events_manual(user, event, form)  # type: ignore
            else:
                informasjon = "Ugylding action - ingen endringer"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&action={action}&heat={valgt_heat}"
        )


async def create_dns_time_events_manual(user: dict, event: dict, form: dict) -> str:
    """Extract form data and create time_events for start."""
    informasjon = ""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
    request_body = {
        "id": "",
        "bib": 0,
        "event_id": form["event_id"],
        "race": "",
        "race_id": "",
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
    if "bib" in form.keys():
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            try:
                if bib.isnumeric():
                    request_body["timing_point"] = "DNS"
                    changelog_comment = "DNS registrert. "
                    request_body["bib"] = int(bib)
                    request_body["changelog"] = [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["name"],
                            "comment": changelog_comment,
                        }
                    ]
                    # find race - always pick the latest start if several results
                    start_entries = await StartAdapter().get_start_entries_by_bib(user["token"], event["id"], int(bib))
                    if start_entries:
                        start_entry = start_entries[len(start_entries) - 1]
                        race_id = start_entry["race_id"]
                        race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
                        request_body["name"] = start_entry["name"]
                        request_body["club"] = start_entry["club"]
                        request_body["race_id"] = race_id
                        request_body["race"] = f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}"

                    id = await TimeEventsService().create_start_time_event(
                        user["token"], request_body
                    )
                    i += 1
                    informasjon += f" {request_body['bib']}-{changelog_comment}. "
                    logging.debug(f"Registrering: {id} - body: {request_body}")
            except Exception as e:
                informasjon += f"Error: {e}"

    informasjon = f" {i} registreringer lagret. {informasjon}"
    return informasjon


async def create_start_time_events_for_race(user: dict, event: dict, form: dict) -> str:
    """Extract form data and create time_events for start."""
    informasjon = ""
    time_stamp_now = EventsAdapter().get_local_time(event, "log")
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
            logging.debug(f"Registrering: {id} - body: {request_body}")
    informasjon = f" {i} registreringer lagret. "
    return informasjon


async def get_passeringer(token: str, event_id: str, action: str) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    if action == "control" or action == "Template":
        tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
            token, event_id
        )
        for passering in tmp_passeringer:
            if passering["timing_point"] == "Template":
                if action == "Template":
                    passeringer.append(passering)
            elif passering["status"] == "Error":
                if action == "control":
                    passeringer.append(passering)

    return passeringer
