"""Resource module for resultat view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    FotoService,
    RaceclassesAdapter,
)
from .utils import check_login_open, get_event, get_results_by_raceclass


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
            resultlist = []  # type: ignore
            valgt_bildevisning = ""
            sportsclubs = str(os.getenv("SPORTS_CLUBS"))
            clubs = sportsclubs.split(",")

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
            try:
                valgt_klubb = self.request.rel_url.query["klubb"]
            except Exception:
                valgt_klubb = ""

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            # ensure web safe urls
            for klasse in raceclasses:
                for ac_name in klasse["ageclasses"]:
                    klasse["KlasseWeb"] = ac_name.replace(" ", "%20")

            if (valgt_klasse == "") and (valgt_klubb == ""):
                informasjon = "Velg klasse eller klubb for å vise resultater"
            else:
                if valgt_klubb != "":
                    foto = await FotoService().get_foto_by_klubb(
                        user, valgt_klubb, event_id
                    )
                    valgt_bildevisning = "klubb=" + valgt_klubb
                else:
                    resultlist = await get_results_by_raceclass(
                        user, event_id, valgt_klasse
                    )
                    if len(resultlist) == 0:
                        informasjon = "Resultatliste er ikke klar. Følg med på <a href=>live resultater</a>."
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
                    "valgt_klubb": valgt_klubb,
                    "klasser": raceclasses,
                    "clubs": clubs,
                    "resultatliste": resultlist,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
