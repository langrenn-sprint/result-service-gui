"""Resource module for resultat view."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    FotoService,
    KjoreplanService,
    RaceclassesAdapter,
    ResultatHeatService,
    ResultatService,
)
from .utils import check_login, get_event


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
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            foto = []
            informasjon = ""
            resultatliste = []
            heatliste = []
            resultatheatliste = []
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

            klasser = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )
            # ensure web safe urls
            for klasse in klasser:
                klasse["KlasseWeb"] = klasse["name"].replace(" ", "%20")

            if (valgt_klasse == "") and (valgt_klubb == ""):
                informasjon = "Velg klasse eller klubb for å vise resultater"
            elif valgt_klasse == "":
                # get resultat by klubb
                resultatliste = await ResultatService().get_resultatliste_by_klubb(
                    self.request.app["db"],
                    valgt_klubb,
                )
                foto = await FotoService().get_foto_by_klubb(
                    self.request.app["db"], valgt_klubb, event
                )
                valgt_bildevisning = "klubb=" + valgt_klubb
            else:
                # get resultat by klasse - sluttresultat
                resultatliste = await ResultatService().get_resultatliste_by_klasse(
                    self.request.app["db"],
                    valgt_klasse,
                )
                # heatresultater
                heatliste = await KjoreplanService().get_heat_by_klasse(
                    self.request.app["db"],
                    valgt_klasse,
                )
                resultatheatliste = (
                    await ResultatHeatService().get_resultatheat_by_klasse(
                        self.request.app["db"],
                        valgt_klasse,
                    )
                )
                foto = await FotoService().get_foto_by_klasse(
                    self.request.app["db"], valgt_klasse, event
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
                    "klasser": klasser,
                    "clubs": clubs,
                    "resultatliste": resultatliste,
                    "heatliste": heatliste,
                    "resultatheatliste": resultatheatliste,
                    "username": user["username"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that creates a collection of athletes."""
        body = await self.request.json()
        logging.debug(f"Got request-body {body} of type {type(body)}")
        result = await ResultatService().create_resultatliste(
            self.request.app["db"], body
        )
        return web.Response(status=result)


class ResultatHeat(web.View):
    """Class representing the resultat heat view."""

    async def post(self) -> web.Response:
        """Post route function that creates a collection of athletes."""
        body = await self.request.json()
        logging.debug(f"Got request-body {body} of type {type(body)}")
        result = await ResultatHeatService().create_resultatheat(
            self.request.app["db"], body
        )
        return web.Response(status=result)
