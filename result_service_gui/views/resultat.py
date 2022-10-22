"""Resource module for resultat view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    PhotosAdapter,
    RaceclassesAdapter,
    RaceclassResultsAdapter,
    RaceclassResultsService,
    RaceplansAdapter,
)
from .utils import (
    check_login_open,
    get_event,
)


class Resultat(web.View):
    """Class representing the resultat view. Both sluttresultat and heatresultat."""

    async def get(self) -> web.Response:
        """Get route function."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login_open(self)
            event = await get_event(user, event_id)

            foto = []
            informasjon = ""
            resultlist = {}
            valgt_bildevisning = ""

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            if not valgt_klasse:
                informasjon = "Velg klasse for å vise resultater"
                foto = await PhotosAdapter().get_all_photos(user["token"], event_id, 5)
            else:
                try:
                    resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                        event_id, valgt_klasse
                    )
                except Exception:
                    informasjon = "Resultater er ikke klare. Velg 'Live' i menyen for heat resultater"

                foto = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_klasse, 5
                )
                valgt_bildevisning = "klasse=" + valgt_klasse

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "resultat.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "foto": foto,
                    "informasjon": informasjon,
                    "valgt_bildevisning": valgt_bildevisning,
                    "valgt_klasse": valgt_klasse,
                    "klasser": raceclasses,
                    "resultlist": resultlist,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def get_races_for_result_view(
    token: str, event_id: str, valgt_klasse: str
) -> list:
    """Extract races with enriched results."""
    races = []
    _tmp_races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )
    for _tmp_race in _tmp_races:
        race = await RaceplansAdapter().get_race_by_id(token, _tmp_race["id"])
        race["finish_results"] = RaceclassResultsService().get_finish_rank_for_race(
            race
        )
        races.append(race)
    return races
