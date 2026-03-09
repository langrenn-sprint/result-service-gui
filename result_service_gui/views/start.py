"""Resource module for start resources."""

import asyncio
import logging
import time
from operator import itemgetter

import aiohttp_jinja2
from aiohttp import web

from result_service_gui.services import (
    EventsAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
    TimeEventsAdapter,
)

from .utils import (
    build_enriched_startlist,
    check_login_open,
    get_display_style,
    get_event,
    get_qualification_text,
    get_raceplan_summary,
    get_races_for_live_view,
)


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

            races = []
            raceplan_summary = []
            colseparators = []
            colclass = "w3-container"
            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""
                informasjon += "Viser kjøreplan. Velg klasse for å se startlister."
            try:
                valgt_runde = self.request.rel_url.query["runde"]
            except Exception:
                valgt_runde = ""

            t0 = time.monotonic()
            # Parallel: fetch raceclasses and all races simultaneously
            raceclasses, all_races = await asyncio.gather(
                RaceclassesAdapter().get_raceclasses(user["token"], event_id),
                RaceplansAdapter().get_all_races(user["token"], event_id),
            )
            logging.debug(
                f"start: initial fetches done in {time.monotonic() - t0:.3f}s "
                f"({len(all_races)} races, {len(raceclasses)} classes)"
            )

            # Select relevant races and set layout
            if valgt_klasse == "now":
                selected_races = get_races_for_live_view(event, all_races, 0, 9)
                summary_races = selected_races
                colseparators = [3, 6]
                colclass = "w3-third"
            else:
                selected_races = [
                    r for r in all_races if r["raceclass"] == valgt_klasse
                ]
                summary_races = all_races

            if len(selected_races) == 0:
                informasjon = f"{informasjon} Ingen løp funnet."
            else:
                t1 = time.monotonic()

                async def fetch_race_data(race_summary: dict) -> dict:
                    """Fetch full race details and time events in parallel."""
                    try:
                        race, time_events = await asyncio.gather(
                            RaceplansAdapter().get_race_by_id(
                                user["token"], race_summary["id"]
                            ),
                            TimeEventsAdapter().get_time_events_by_race_id(
                                user["token"], race_summary["id"]
                            ),
                        )
                    except Exception:
                        logging.exception(
                            f"start: failed to fetch data for race {race_summary['id']}"
                        )
                        raise
                    race["next_race"] = get_qualification_text(race)
                    race["display_color"] = get_display_style(
                        race["start_time"], event
                    )
                    race["start_time"] = race["start_time"][-8:]
                    race["startliste"] = build_enriched_startlist(race, time_events)
                    return race

                # Parallel: fetch all selected races (details + time events) at once
                races = list(
                    await asyncio.gather(
                        *[fetch_race_data(r) for r in selected_races]
                    )
                )
                logging.debug(
                    f"start: fetched {len(races)} races with startlists "
                    f"in {time.monotonic() - t1:.3f}s"
                )
                raceplan_summary = get_raceplan_summary(summary_races, raceclasses)

            # filter on selected round
            if valgt_runde:
                filtered_races = []
                for race in races:
                    if race["round"] == valgt_runde:
                        filtered_races.append(race)
                races = filtered_races

            # sort start list by starting position
            for race in races:
                if len(race["startliste"]) > 1:
                    race["startliste"] = sorted(
                        race["startliste"], key=itemgetter("starting_position")
                    )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start.html",
                self.request,
                {
                    "colclass": colclass,
                    "colseparators": colseparators,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "valgt_runde": valgt_runde,
                    "raceclasses": raceclasses,
                    "races": races,
                    "raceplan_summary": raceplan_summary,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.exception("Error. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
