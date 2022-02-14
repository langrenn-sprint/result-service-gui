"""Resource module for resultat view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    FotoService,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login_open,
    get_event,
    get_finish_rank,
    get_results_by_raceclass,
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
            races = []
            informasjon = ""
            resultlist = []  # type: ignore
            valgt_bildevisning = ""

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            # ensure web safe urls
            for klasse in raceclasses:
                for ac_name in klasse["ageclasses"]:
                    klasse["KlasseWeb"] = ac_name.replace(" ", "%20")

            if valgt_klasse == "":
                informasjon = "Velg klasse for å vise resultater"
            else:
                resultlist = await get_results_by_raceclass(
                    user, event_id, valgt_klasse
                )
                if len(resultlist) == 0:
                    informasjon = "Resultater er ikke klare. Velg 'Live' i menyen for heat resultater"
                else:
                    races = await get_races_for_result_view(
                        user["token"], event_id, valgt_klasse
                    )

                    foto = await FotoService().get_foto_by_klasse(
                        user, valgt_klasse, event_id
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
                    "races": races,
                    "resultatliste": resultlist,
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
        race["finish_results"] = get_finish_rank(race)
        races.append(race)
    return races
