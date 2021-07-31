"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from result_service_gui.services import EventsAdapter
from result_service_gui.services import UserAdapter


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
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
            return web.HTTPSeeOther(location=f"/login?event={eventid}")
        username = session["username"]
        token = session["token"]

        event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
        if eventid != "":
            logging.debug(f"get_event {eventid}")
            event = await EventsAdapter().get_event(token, eventid)

        return await aiohttp_jinja2.render_template_async(
            "events.html",
            self.request,
            {
                "lopsinfo": "Arrangement",
                "event": event,
                "eventid": eventid,
                "informasjon": informasjon,
                "username": username,
            },
        )
