"""Resource module for verificatoin of timing registration."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
)
from .utils import (
    check_login,
    create_finish_time_events,
    get_enchiced_startlist,
    get_event,
    get_finish_timings,
    get_passeringer,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
)


class TimingVerify(web.View):
    """Class representing the timing admin view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        current_races = []
        next_races = []
        next_round = []
        valgt_runde = {
            "klasse": "",
            "runde": "",
        }

        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login(self)
            event_id = self.request.rel_url.query["event_id"]
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            all_races = await RaceplansAdapter().get_all_races(user["token"], event_id)

            # check if specific round is selected
            try:
                valgt_runde["klasse"] = self.request.rel_url.query["klasse"]
                valgt_runde["runde"] = self.request.rel_url.query["runde"]
            except Exception:
                # if heat is selected, find round
                try:
                    heat = int(self.request.rel_url.query["heat"])
                    valgt_runde = await find_round(all_races, heat)
                except Exception:
                    informasjon = f"Velg runde i menyen. {informasjon}"

            next_round = get_next_round(valgt_runde)

            raceplan_summary = []
            if len(all_races) == 0:
                informasjon = f"{informasjon} Ingen kjøreplaner funnet."
            else:
                raceplan_summary = get_raceplan_summary(all_races, raceclasses)

            # filter for selected races and enrich
            for race in all_races:
                if valgt_runde["klasse"] == race["raceclass"]:
                    if valgt_runde["runde"] == race["round"]:
                        race["next_race"] = get_qualification_text(race)
                        # get start list detail
                        race["startliste"] = await get_enchiced_startlist(
                            user, race["id"]
                        )
                        race["finish_timings"] = await get_finish_timings(
                            user, race["id"]
                        )

                        current_races.append(race)
                    elif race["round"] in next_round:
                        # get start list detail
                        race["startliste"] = await get_enchiced_startlist(
                            user, race["id"]
                        )
                        next_races.append(race)

            # get passeringer with error
            error_passeringer = await get_passeringer(
                user["token"], event_id, "control", valgt_runde["klasse"]
            )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing_verify.html",
                self.request,
                {
                    "error_passeringer": error_passeringer,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "next_races": next_races,
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
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            valgt_runde["klasse"] = str(form["klasse"])
            valgt_runde["runde"] = str(form["runde"])

            if "publish_results" in form.keys():
                informasjon = "Resultater er publisert (TODO)"
            elif "add_result" in form.keys():
                informasjon = await add_result(user, form)  # type: ignore
            elif "create_start" in form.keys():
                informasjon = await create_start(user, form)  # type: ignore
            elif "delete_start" in form.keys():
                informasjon = await delete_start(user, form)  # type: ignore
            elif "update_result" in form.keys():
                informasjon = await update_result(user, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
        info = (
            f"{informasjon}&klasse={valgt_runde['klasse']}&runde={valgt_runde['runde']}"
        )
        return web.HTTPSeeOther(
            location=f"/timing_verify?event_id={event_id}&informasjon={info}"
        )


async def add_result(user: dict, form: dict) -> str:
    """Extract form data and update one result and corresponding start event."""
    rank_identifier = f"form_rank_{form['rank']}"
    new_result = {
        "event_id": form["event_id"],
        "race": form["race"],
        "race_id": form["race_id"],
        rank_identifier: form["bib"],
    }
    informasjon = await create_finish_time_events(user, "finish_bib", new_result)  # type: ignore
    return informasjon


async def create_start(user: dict, form: dict) -> str:
    """Extract form data and create one start."""
    contestant = await ContestantsAdapter().get_contestant_by_bib(
        user["token"], form["event_id"], form["bib"]
    )

    new_start = {
        "startlist_id": form["startlist_id"],
        "race_id": form["race_id"],
        "bib": form["bib"],
        "starting_position": form["starting_position"],
        "scheduled_start_time": form["start_time"],
        "name": f"{contestant['first_name']} {contestant['last_name']}",
        "club": contestant["club"],
    }
    id = await StartAdapter().create_start_entry(user["token"], new_start)
    informasjon = f"Opprettet ny start. Resultat: {id}"
    return informasjon


async def delete_start(user: dict, form: dict) -> str:
    """Extract form data and delete one start event."""
    informasjon = "delete_start"
    id = await StartAdapter().delete_start_entry(
        user["token"], form["race_id"], form["start_id"]
    )
    informasjon = f"Slettet start. Resultat: {id}"
    return informasjon


async def find_round(all_races, heat) -> dict:
    """Analyse selected round and determine next round(s)."""
    valgt_runde = {
        "klasse": "",
        "runde": "",
    }
    if heat == 0:
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
            if heat == race["order"]:
                valgt_runde = {
                    "klasse": race["raceclass"],
                    "runde": race["round"],
                }
                break
    return valgt_runde


def get_next_round(valgt_runde: dict) -> list:
    """Analyse selected round and determine next round(s)."""
    next_round = []
    if valgt_runde["runde"] == "Q":
        next_round = ["S", "F"]
    elif valgt_runde["runde"] == "S":
        next_round = ["F"]
    elif valgt_runde["runde"] == "N":
        next_round = ["Q"]
    return next_round


async def update_result(user: dict, form: dict) -> str:
    """Extract form data and update one result and corresponding start event."""
    informasjon = await create_finish_time_events(user, "finish_bib", form)  # type: ignore
    return informasjon
