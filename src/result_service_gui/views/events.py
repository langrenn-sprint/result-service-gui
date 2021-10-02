"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session

from result_service_gui.services import UserAdapter
from .utils import get_event


class Events(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the events page."""
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
                return web.HTTPSeeOther(location=f"/login?event={event_id}")
            username = session["username"]
            token = session["token"]

            event = await get_event(token, event_id)

            return await aiohttp_jinja2.render_template_async(
                "events.html",
                self.request,
                {
                    "lopsinfo": "Arrangement",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": username,
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Starting new session.")
            session.invalidate()
            return web.HTTPSeeOther(location="/login")
