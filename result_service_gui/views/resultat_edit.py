"""Resource module for verificatoin of timing registration."""
import datetime
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    ContestantsAdapter,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceclassResultsService,
    RaceplansAdapter,
    ResultAdapter,
    StartAdapter,
)
from .utils import (
    check_login,
    get_enrichced_startlist,
    get_event,
    get_finish_timings,
    get_passeringer,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
    update_finish_time_events,
)


class ResultatEdit(web.View):
    """Class representing the result edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        current_races = []
        raceplan_summary = []
        error_passeringer = []
        valgt_runde = {
            "klasse": "",
            "runde": "",
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
                    all_races = await RaceplansAdapter().get_all_races(
                        user["token"], event_id
                    )
                    valgt_runde = await find_round(all_races, heat)
                except Exception:
                    informasjon = f"Velg runde i menyen. {informasjon}"
                    logging.debug("Ingen runde valgt")

            all_races = await RaceplansAdapter().get_races_by_racesclass(
                user["token"], event_id, valgt_runde["klasse"]
            )
            if len(all_races) == 0:
                informasjon = f"{informasjon} Ingen kjøreplaner funnet."

            raceplan_summary = get_raceplan_summary(all_races, raceclasses)

            if valgt_runde["klasse"]:
                foto = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_runde["klasse"], 4
                )
                # filter for selected races and enrich
                for race in all_races:
                    if valgt_runde["runde"] == race["round"]:
                        race["next_race"] = get_qualification_text(race)
                        # get start list detail
                        race["startliste"] = await get_enrichced_startlist(user, race)
                        race["finish_timings"] = await get_finish_timings(
                            user, race["id"]
                        )
                        race["photo_finish"] = get_foto_finish_for_race(user, race, foto)
                        race["photo_start"] = get_foto_start_for_race(user, race, foto)
                        race["photo_bib_rank"] = get_finish_rank_from_photos(
                            user, race["photo_finish"], "right"
                        )
                        current_races.append(race)

                # get passeringer with error
                error_passeringer = await get_passeringer(
                    user["token"], event_id, "control", valgt_runde["klasse"]
                )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "resultat_edit.html",
                self.request,
                {
                    "error_passeringer": error_passeringer,
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

    async def post(self) -> web.Response:
        """Post route function that creates deltakerliste."""
        # check login
        user = await check_login(self)
        informasjon = ""
        valgt_runde = {}
        form = await self.request.post()
        try:
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            valgt_runde["klasse"] = str(form["klasse"])
            valgt_runde["runde"] = str(form["runde"])

            if "create_start" in form.keys():
                informasjon += "<br>" + await create_start(user, form)  # type: ignore
            elif "update_result" in form.keys():
                informasjon += "<br>" + await update_result(user, form)  # type: ignore
                # set results to official
                if "publish" in form.keys():
                    res = await ResultAdapter().update_result_status(user["token"], form["race_id"], 2)  # type: ignore
                    informasjon = f"Heat resultat er publisert ({res}). <br>" + informasjon
                    race_round = str(form["race"])
                    if race_round.find("FA") > -1:
                        res = await RaceclassResultsService().create_raceclass_results(
                            user["token"], event_id, valgt_runde["klasse"]
                        )  # type: ignore
                        informasjon = f" Klassens resultat er publisert ({res}). " + informasjon
        except Exception as e:
            logging.error(f"Error: {e}")
            error_reason = str(e)
            if error_reason.startswith("401"):
                informasjon = f"Error 401 - Ingen tilgang, vennligst logg inn på nytt. {e}"
                # check for update without reload
                if "ajax" in form.keys():
                    return web.Response(text=informasjon)
                return web.HTTPSeeOther(
                    location=f"/login?informasjon={informasjon}"
                )
            informasjon += f"Det har oppstått en feil - {e.args}. " + informasjon
        # check for update without reload
        if "ajax" in form.keys():
            return web.Response(text=informasjon)
        info = (
            f"{informasjon}&klasse={valgt_runde['klasse']}&runde={valgt_runde['runde']}"
        )
        return web.HTTPSeeOther(
            location=f"/resultat_edit?event_id={event_id}&informasjon={info}"
        )


async def create_start(user: dict, form: dict) -> str:
    """Extract form data and create one start."""
    informasjon = ""
    contestant = await ContestantsAdapter().get_contestant_by_bib(
        user["token"], form["event_id"], form["bib"]
    )

    new_start = {
        "startlist_id": form["startlist_id"],
        "race_id": form["race_id"],
        "bib": int(form["bib"]),
        "starting_position": int(form["starting_position"]),
        "scheduled_start_time": form["start_time"],
        "name": f"{contestant['first_name']} {contestant['last_name']}",
        "club": contestant["club"],
    }
    id = await StartAdapter().create_start_entry(user["token"], new_start)
    informasjon += f"Lagt til bib {form['bib']} i startliste."
    logging.debug(f"Opprettet start {id}")
    return informasjon


async def find_round(all_races: list, heat_order: int) -> dict:
    """Analyse selected round and determine next round(s)."""
    valgt_runde = {
        "klasse": "",
        "runde": "",
    }
    if heat_order == 0:
        # find race starting now
        races = get_races_for_live_view(all_races, 0, 1)
        if len(races) > 0:
            valgt_runde = {
                "klasse": races[0]["raceclass"],
                "runde": races[0]["round"],
            }
    else:
        # find round for selected heat
        for race in all_races:
            if heat_order == race["order"]:
                valgt_runde = {
                    "klasse": race["raceclass"],
                    "runde": race["round"],
                }
                break
    return valgt_runde


def get_foto_finish_for_race(user: dict, race: dict, photos: list) -> list:
    """Loop throgh photos and return relevant finish photo(s)."""
    fotos = []
    for photo in photos:
        if photo["race_id"] == race["id"]:
            if photo["is_photo_finish"]:
                fotos.append(photo)
    return fotos


def get_foto_start_for_race(user: dict, race: dict, photos: list) -> list:
    """Loop throgh photos and return relevant finish photo(s)."""
    fotos = []
    for photo in photos:
        if photo["race_id"] == race["id"]:
            if photo["is_start_registration"]:
                fotos.append(photo)
    return fotos


def get_finish_rank_from_photos(user: dict, photos: list, camera_side: str) -> list:
    """Loop throgh photos and return bib(s) in sorted order."""
    biblist = []
    for photo in photos:
        if camera_side == "left":
            for bib in photo["biblist"]:
                if bib not in biblist:
                    biblist.append(bib)
        else:
            for bib in reversed(photo["biblist"]):
                if bib not in biblist:
                    biblist.append(bib)
    return biblist


async def update_result(user: dict, form: dict) -> str:
    """Extract form data and update result and corresponding start event."""
    time_now = datetime.datetime.now()
    time_stamp_now = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}-{time_now.strftime('%d')}T{time_now.strftime('%X')}"
    delete_result_list = []
    add_result_list = []
    for x in form.keys():
        bib_changed = True
        if x.startswith("form_rank_"):
            new_bib = form[x]
            _rank = int(x[10:])
            # check if anything is changed and delete old registration
            if form[f"old_form_rank_{_rank}"]:
                old_bib = form[f"old_form_rank_{_rank}"]
                if old_bib == new_bib:
                    bib_changed = False
                else:
                    # append time event to be deleted
                    delete_entry = {
                        "time_event_id": form[f"time_event_id_{_rank}"],
                    }
                    delete_result_list.append(delete_entry)
            if new_bib.isnumeric() and bib_changed:
                # append new entry
                new_entry = {
                    "id": "",
                    "bib": int(new_bib),
                    "event_id": form["event_id"],
                    "race": form["race"],
                    "race_id": form["race_id"],
                    "timing_point": form["timing_point"],
                    "rank": _rank,
                    "registration_time": time_stamp_now,
                    "next_race": "",
                    "next_race_id": "",
                    "next_race_position": 0,
                    "status": "OK",
                    "changelog": [
                        {
                            "timestamp": time_stamp_now,
                            "user_id": user["name"],
                            "comment": f"{_rank} plass i mål. ",
                        }
                    ],
                }
                add_result_list.append(new_entry)

    informasjon = await update_finish_time_events(user, delete_result_list, add_result_list)  # type: ignore
    return informasjon
