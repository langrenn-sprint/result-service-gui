"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from result_service_gui.services import (
    EventsAdapter,
    KjoreplanService,
    RaceclassesAdapter,
    StartListeService,
    UserAdapter,
)


class Start(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the startlister page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        # check login
        username = ""
        session = await get_session(self.request)
        try:
            loggedin = UserAdapter().isloggedin(session)
            if not loggedin:
                return web.HTTPSeeOther(location="/login")
            username = session["username"]
            token = session["token"]
            event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
            if event_id != "":
                logging.debug(f"get_event {event_id}")
                event = await EventsAdapter().get_event(token, event_id)

            informasjon = ""
            startliste = []
            kjoreplan = []
            colseparators = []
            colclass = "w3-half"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
                informasjon = "Velg klasse for å se startlister."

            klasser = await RaceclassesAdapter().get_ageclasses(token, event_id)

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
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "colseparators": colseparators,
                    "colclass": colclass,
                    "klasser": klasser,
                    "kjoreplan": kjoreplan,
                    "startliste": startliste,
                    "username": username,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Starting new session.")
            session.invalidate()
            return web.HTTPSeeOther(location="/login")

    async def post(self) -> web.Response:
        """Post route function that creates a collection of athletes."""
        body = await self.request.json()
        logging.debug(f"Got request-body {body} of type {type(body)}")
        result = await StartListeService().create_startliste(
            self.request.app["db"], body
        )
        return web.Response(status=result)
