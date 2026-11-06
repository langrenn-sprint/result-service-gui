"""Resource module for main view."""

import logging

import aiohttp_jinja2
from aiohttp import web

from result_service_gui.adapters import EventsAdapter

from .utils import check_login_open, error_text, get_event, is_login_error, raise_error


class Main(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            reload = self.request.rel_url.query["reload"]
        except Exception:
            reload = ""

        try:
            user = await check_login_open(self)
            event = await get_event(user, "")

            events = await EventsAdapter().get_all_events(user["token"])
            logging.debug(f"Events: {events}")

            return await aiohttp_jinja2.render_template_async(
                "index.html",
                self.request,
                {
                    "lopsinfo": "Langrenn-sprint",
                    "event": event,
                    "event_id": "",
                    "events": events,
                    "informasjon": informasjon,
                    "reload": reload,
                    "username": user["name"],
                },
            )
        except Exception as e:
            if is_login_error(e):
                raise_error(self, e)
            # The other pages send errors here, so show an error page instead:
            logging.exception("Error on the main page")
            return await aiohttp_jinja2.render_template_async(
                "error.html",
                self.request,
                {"informasjon": error_text(e)},
                status=web.HTTPInternalServerError.status_code,
            )
