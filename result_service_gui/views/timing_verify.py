"""Resource module for verificatoin of timing registration."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    ContestantsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
    create_finish_time_events,
    get_enchiced_startlist,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
)


class TimingVerify(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        informasjon = ""
        selected_races = []
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
            action = "result"
        try:
            valgt_runde = self.request.rel_url.query["valgt_runde"]
        except Exception:
            valgt_runde = ""
            informasjon = f"Velg runde i menyen. {informasjon}"

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            all_races = await RaceplansAdapter().get_all_races(user["token"], event_id)
            raceplan_summary = []
            if len(all_races) == 0:
                informasjon = f"{informasjon} Ingen kjøreplaner funnet."
            else:
                raceplan_summary = get_raceplan_summary(all_races, raceclasses)

            # filter for selected races and enrich
            for race in all_races:
                current_round = f"{race['raceclass']}{race['round']}"
                if valgt_runde == current_round:
                    race["next_race"] = get_qualification_text(race)
                    # get start list detail
                    race["startliste"] = await get_enchiced_startlist(user, race["id"])
                    selected_races.append(race)

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "timing_verify.html",
                self.request,
                {
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "raceclasses": raceclasses,
                    "raceplan_summary": raceplan_summary,
                    "races": selected_races,
                    "username": user["username"],
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
        action = ""
        try:
            form = await self.request.post()
            logging.debug(f"Form {form}")
            event_id = str(form["event_id"])
            action = str(form["action"])
            valgt_runde = str(form["valgt_runde"])

            if "publish_results" in form.keys():
                informasjon = "Resultater er publisert (TODO)"
            elif "create_start" in form.keys():
                informasjon = await create_start(user, form)  # type: ignore
            elif "delete_result" in form.keys():
                informasjon = await delete_result(user, form)  # type: ignore
            elif "delete_start" in form.keys():
                informasjon = await delete_start(user, form)  # type: ignore
            elif "update_result" in form.keys():
                informasjon = await update_result(user, form)  # type: ignore
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."

        return web.HTTPSeeOther(
            location=f"/timing_verify?event_id={event_id}&informasjon={informasjon}&action={action}&valgt_runde={valgt_runde}"
        )


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


async def delete_result(user: dict, form: dict) -> str:
    """Extract form data and delete one result and corresponding start event."""
    informasjon = ""

    # get time event and delete next start if existing
    time_event = await TimeEventsAdapter().get_time_event_by_id(
        user["token"], form["time_event_id"]
    )
    if len(time_event["next_race_id"]) > 0:
        start_entries = await StartAdapter().get_start_entries_by_race_id(
            user["token"], time_event["next_race_id"]
        )
        for start_entry in start_entries:
            if time_event["bib"] == start_entry["bib"]:
                id = await StartAdapter().delete_start_entry(
                    user["token"], start_entry["race_id"], start_entry["id"]
                )
                informasjon = f"Slettet start entry i neste heat. Resultat: {id}"
    id2 = await TimeEventsAdapter().delete_time_event(
        user["token"], form["time_event_id"]
    )
    informasjon = f"Slettet målpassering. Resultat: {id2}  {informasjon}"
    return informasjon


async def delete_start(user: dict, form: dict) -> str:
    """Extract form data and delete one start event."""
    informasjon = "delete_start"
    id = await StartAdapter().delete_start_entry(
        user["token"], form["race_id"], form["start_id"]
    )
    informasjon = f"Slettet start. Resultat: {id}"
    return informasjon


async def update_result(user: dict, form: dict) -> str:
    """Extract form data and update one result and corresponding start event."""
    informasjon = await create_finish_time_events(user, "finish_bib", form)  # type: ignore
    return informasjon
