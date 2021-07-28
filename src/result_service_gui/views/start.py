"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from result_service_gui.services import (
    EventsAdapter,
    KjoreplanService,
    KlasserService,
    StartListeService,
    UserAdapter,
)


class Start(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the startlister page."""
        try:
            eventid = self.request.rel_url.query["eventid"]
        except Exception:
            eventid = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        # check login
        username = ""
        session = await get_session(self.request)
        loggedin = UserAdapter().isloggedin(session)
        if not loggedin:
            return web.HTTPSeeOther(location="/login")
        username = session["username"]
        token = session["token"]
        event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
        if eventid != "":
            logging.debug(f"get_event {eventid}")
            event = await EventsAdapter().get_event(token, eventid)

        informasjon = ""
        startliste = []
        kjoreplan = []
        klassetider = {}
        colseparators = []
        colclass = "w3-half"

        try:
            valgt_klasse = self.request.rel_url.query["klasse"]
        except Exception:
            valgt_klasse = ""  # noqa: F841
            informasjon = "Velg klasse for å se startlister."

        klasser = await KlasserService().get_all_klasser(self.request.app["db"])

        if valgt_klasse == "live":
            # vis heat som starter nå
            colclass = "w3-third"
            iantallheat = 10
            isplitt = [3, 6]
            kjoreplan = await KjoreplanService().get_upcoming_heat(
                self.request.app["db"], iantallheat
            )
            i = 0
            for heat in kjoreplan:
                logging.debug(heat["Index"])
                _liste = await StartListeService().get_startliste_by_heat(
                    self.request.app["db"], heat["Index"]
                )
                if i in isplitt:
                    colseparators.append(heat["Index"])
                    logging.debug(colseparators)
                i += 1
                for loper in _liste:
                    startliste.append(loper)
                logging.debug(startliste)
        else:
            # get startlister for klasse
            klassetider = await KlasserService().get_klasse_by_lopsklasse(
                self.request.app["db"], valgt_klasse
            )
            kjoreplan = await KjoreplanService().get_heat_by_klasse(
                self.request.app["db"], valgt_klasse
            )
            startliste = await StartListeService().get_startliste_by_lopsklasse(
                self.request.app["db"], valgt_klasse
            )

        logging.debug(startliste)

        """Get route function."""
        return await aiohttp_jinja2.render_template_async(
            "start.html",
            self.request,
            {
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "valgt_klasse": valgt_klasse,
                "colseparators": colseparators,
                "colclass": colclass,
                "klasser": klasser,
                "klassetider": klassetider,
                "kjoreplan": kjoreplan,
                "startliste": startliste,
                "username": username,
            },
        )

    async def post(self) -> web.Response:
        """Post route function that creates a collection of athletes."""
        body = await self.request.json()
        logging.debug(f"Got request-body {body} of type {type(body)}")
        result = await StartListeService().create_startliste(
            self.request.app["db"], body
        )
        return web.Response(status=result)
