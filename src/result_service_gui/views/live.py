"""Resource module for live resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_enchiced_startlist,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
)


class Live(web.View):
    """Class representing the live view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            races = []
            raceplan_summary = []
            colseparators = []
            colclass = "w3-half"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
                informasjon += "Velg klasse for å se live lister."
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            try:
                valgt_startnr = self.request.rel_url.query["startnr"]
            except Exception:
                valgt_startnr = ""

            colseparators = []
            colclass = "w3-third"
            if valgt_startnr == "":

                # get startlister for klasse
                _tmp_races = await RaceplansAdapter().get_all_races(
                    user["token"], event_id
                )
                if len(_tmp_races) == 0:
                    informasjon = f"{informasjon} Ingen kjøreplaner funnet."
                else:
                    for race in _tmp_races:
                        # todo - bruk get_all_races_by_event_id_and_raceclass
                        if race["raceclass"] == valgt_klasse:
                            race["next_race"] = get_qualification_text(race)
                            race["start_time"] = race["start_time"][-8:]
                            colseparators.append(race["round"])
                            # get start list details
                            race["startliste"] = await get_enchiced_startlist(
                                user, race["id"], race["start_entries"]
                            )
                            races.append(race)

                # responsive design - determine column-arrangement
                colseparators = ["KA1", "KA5", "SC1", "SA1", "F1", "F5", "A1", "A5"]
                icolcount = 0
                for heat in races:
                    logging.info(heat)
                    heat_code = f"{heat['round']}{heat['index']}{heat['heat']}"
                    if heat_code in colseparators:
                        icolcount += 1
                        colseparators.append(heat["order"])
                    elif heat["round"] == "F":
                        icolcount += 1
                        colseparators.append(heat["order"])
                        break
                if icolcount == 4:
                    colclass = "w3-quart"

            else:
                # only selected racer

                valgt_startnr = "Startnr: " + valgt_startnr + ", "

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "live.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "valgt_startnr": valgt_startnr,
                    "colseparators": colseparators,
                    "colclass": colclass,
                    "raceclasses": raceclasses,
                    "races": races,
                    "raceplan_summary": raceplan_summary,
                    "username": user["username"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
