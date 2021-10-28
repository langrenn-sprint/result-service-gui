"""Resource module for live view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    DeltakereService,
    KjoreplanService,
    RaceclassesAdapter,
    ResultatHeatService,
    StartAdapter,
)
from .utils import check_login, get_event


class Live(web.View):
    """Class representing the live view."""

    # TODO: reduser kompleksistet i denne funksjonen
    async def get(self) -> web.Response:  # noqa: C901
        """Get route function that return the live result page."""
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

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
                logging.debug(valgt_klasse)
            except Exception:
                valgt_klasse = ""
                informasjon = "Velg klasse for å se live resultater."

            try:
                valgt_startnr = self.request.rel_url.query["startnr"]
            except Exception:
                valgt_startnr = ""

            klasser = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            deltakere = await DeltakereService().get_deltakere_by_lopsklasse(
                self.request.app["db"], valgt_klasse
            )
            logging.debug(deltakere)

            kjoreplan = []
            startliste = []
            resultatliste = []
            colseparators = []
            colclass = "w3-third"
            if valgt_startnr == "":

                kjoreplan = await KjoreplanService().get_heat_for_live_scroll(
                    self.request.app["db"], valgt_klasse
                )

                # responsive design - determine column-arrangement
                colseparators = ["KA1", "KA5", "SC1", "SA1", "F1", "F5", "A1", "A5"]
                icolcount = 0
                for heat in kjoreplan:
                    if heat["Heat"] in colseparators:
                        icolcount += 1
                        if (heat["Heat"] == "SC1") and heat["resultat_registrert"]:
                            colseparators.remove("SC1")
                    elif heat["Heat"] in {"FA", "FB", "FC"}:
                        icolcount += 1
                        colseparators.append(heat["Heat"])
                        break
                if icolcount == 4:
                    colclass = "w3-quart"
                colseparators.remove("KA1")
                colseparators.remove("F1")

                startliste = await StartAdapter().get_startliste_by_lopsklasse(
                    user["token"], event_id, valgt_klasse
                )
                logging.debug(startliste)

                resultatliste = await ResultatHeatService().get_resultatheat_by_klasse(
                    self.request.app["db"], valgt_klasse
                )

            else:
                # only selected racer
                logging.debug(valgt_startnr)

                startliste = await StartAdapter().get_startlist_by_bib(
                    user["token"],
                    event_id,
                    valgt_startnr,
                )
                logging.debug(startliste)

                for start in startliste:
                    _heat = await KjoreplanService().get_heat_by_index(
                        self.request.app["db"],
                        start["Heat"],
                    )
                    kjoreplan.append(_heat)
                    if valgt_klasse == "":
                        valgt_klasse = start["Løpsklasse"]
                        logging.info(valgt_klasse)

                # check for resultat
                resultatliste = await ResultatHeatService().get_resultatheat_by_nr(
                    self.request.app["db"],
                    valgt_startnr,
                )

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
                    "klasser": klasser,
                    "deltakere": deltakere,
                    "kjoreplan": kjoreplan,
                    "resultatliste": resultatliste,
                    "startliste": startliste,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
