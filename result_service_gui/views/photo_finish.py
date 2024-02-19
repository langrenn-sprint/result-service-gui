"""Resource module for verificatoin of timing registration."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
    get_foto_finish_for_race,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
)


class PhotoFinish(web.View):
    """Class representing the photo finish view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        current_races = []
        raceplan_summary = []
        valgt_runde = {
            "klasse": "",
            "runde": "",
            "informasjon": "",
        }

        try:
            informasjon = self.request.rel_url.query["informasjon"]
            info_list = informasjon.split("<br>")
            informasjon = ""
        except Exception:
            informasjon = ""
            info_list = []

        try:
            user = await check_login(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            # check if specific round is selected
            try:
                valgt_runde["klasse"] = self.request.rel_url.query["klasse"]
                valgt_runde["runde"] = self.request.rel_url.query["runde"]
            except Exception:
                # if heat is selected, find round
                try:
                    heat = int(self.request.rel_url.query["heat"])
                    valgt_runde = await find_round(user["token"], event, raceclasses, heat)
                except Exception:
                    informasjon = f"Velg runde i menyen. {informasjon}"
                    logging.debug("Ingen runde valgt")

            all_races = await RaceplansAdapter().get_races_by_racesclass(
                user["token"], event_id, valgt_runde["klasse"]
            )

            raceplan_summary = get_raceplan_summary(all_races, raceclasses)

            if valgt_runde["klasse"]:
                foto = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_runde["klasse"], False
                )
                # filter for selected races and enrich results
                for race in all_races:
                    if valgt_runde["runde"] == race["round"]:
                        race["next_race"] = get_qualification_text(race)
                        race["startliste"] = await get_enrichced_startlist(user, race)
                        race["finish_timings"] = await get_finish_timings(
                            user, race["id"]
                        )
                        race["photo_finish"] = get_foto_finish_for_race(user, race, foto)
                        current_races.append(race)

            if len(current_races) == 0:
                informasjon = f"{informasjon} Ingen heat i denne runden."

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "photo_finish.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "info_list": info_list,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "current_races": current_races,
                    "username": user["name"],
                    "valgt_runde": valgt_runde,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def find_round(token: str, event: dict, raceclasses: list, heat_order: int) -> dict:
    """Analyse selected round and determine next round(s)."""
    valgt_runde = {
        "klasse": "",
        "runde": "",
        "informasjon": "",
    }
    if heat_order == 0:
        all_races = await RaceplansAdapter().get_all_races(
            token, event['id']
        )
        # find race starting now
        races = get_races_for_live_view(event, all_races, 0, 1)
        if len(races) > 0:
            valgt_runde = {
                "klasse": races[0]["raceclass"],
                "runde": races[0]["round"],
                "informasjon": "",
            }
    else:
        # find round for selected heat
        race = await RaceplansAdapter().get_race_by_order(
            token, event["id"], heat_order
        )
        if race:
            valgt_runde = {
                "klasse": race["raceclass"],
                "runde": race["round"],
                "informasjon": "",
            }
            # check if raceclass is without ranking
            for raceclass in raceclasses:
                if race["raceclass"] == raceclass["name"]:
                    if not raceclass['ranking']:
                        valgt_runde["informasjon"] = "OBS: Denne løpsklassen er urangert, resultater vil ikke vises."
    return valgt_runde
