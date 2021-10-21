"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
    TimeEventsAdapter,
)
from .utils import check_login, create_time_event, get_event


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
            registration_mode = self.request.rel_url.query["registration_mode"]
        except Exception:
            registration_mode = ""
            informasjon = f"Velg modus for å se passeringer. {informasjon}"

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            passeringer = []
            colclass = "w3-half"

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            valgt_klasse = ""
            if registration_mode == "heat":
                informasjon = f"{informasjon} Velg heat for å se passeringer."
            elif registration_mode == "raceclass":
                informasjon = f"{informasjon} Velg klasse for å se passeringer."

            # get passeringer for klasse
            race = {}
            try:
                race = await RaceplansAdapter().get_race_by_class(
                    user["token"], event_id, "G12"
                )
            except Exception as e:
                informasjon = str(e)

            passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
                user["token"], event_id
            )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing.html",
                self.request,
                {
                    "colclass": colclass,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "passeringer": passeringer,
                    "race": race,
                    "raceclasses": raceclasses,
                    "registration_mode": registration_mode,
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
        logging.debug(user)

        informasjon = ""
        registration_mode = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])

            # Create new deltakere
            if "start_bib" in form.keys():
                informasjon = await create_time_event(user["token"], "start_bib", form)
                registration_mode = "start_bib"
            elif "start_check" in form.keys():
                informasjon = await create_time_event(
                    user["token"], "start_check", form
                )
                registration_mode = "start_check"
            elif "finish_bib" in form.keys():
                informasjon = await create_time_event(user["token"], "finish_bib", form)
                registration_mode = "finish_bib"
            elif "finish_place" in form.keys():
                informasjon = await create_time_event(
                    user["token"], "finish_place", form
                )
                registration_mode = "finish_place"
            elif "control" in form.keys():
                informasjon = f"Control for {form}."
                registration_mode = "control"
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/timing?event_id={event_id}&informasjon={informasjon}&registration_mode={registration_mode}"
        )
