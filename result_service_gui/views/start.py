"""Resource module for start resources."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login_open,
    get_enchiced_startlist,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
)

EVENT_GUI_HOST_SERVER = os.getenv("EVENT_GUI_HOST_SERVER", "localhost")
EVENT_GUI_HOST_PORT = os.getenv("EVENT_GUI_HOST_PORT", "8080")
EVENT_GUI_URL = f"http://{EVENT_GUI_HOST_SERVER}:{EVENT_GUI_HOST_PORT}"


class Start(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the startlister page."""
        try:
            user = await check_login_open(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user, event_id)

            try:
                informasjon = self.request.rel_url.query["informasjon"]
            except Exception:
                informasjon = ""
            try:
                action = self.request.rel_url.query["action"]
            except Exception:
                action = ""

            races = []
            raceplan_summary = []

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
                informasjon += "Velg klasse for å se startlister."
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            # get relevant races
            _tmp_races = []
            if "live" == valgt_klasse:
                _tmp_races = await get_races_for_live_view(user, event_id, 0, 8)
            else:
                # get startlister for klasse
                _tmp_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
            if len(_tmp_races) == 0:
                informasjon = f"{informasjon} Ingen løp funnet."
            else:
                for race in _tmp_races:
                    if (race["raceclass"] == valgt_klasse) or ("live" == valgt_klasse):
                        race["next_race"] = get_qualification_text(race)
                        race["start_time"] = race["start_time"][-8:]
                        # get start list details
                        race["startliste"] = await get_enchiced_startlist(
                            user, race["id"]
                        )
                        races.append(race)
                raceplan_summary = get_raceplan_summary(_tmp_races, raceclasses)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "raceclasses": raceclasses,
                    "races": races,
                    "raceplan_summary": raceplan_summary,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
