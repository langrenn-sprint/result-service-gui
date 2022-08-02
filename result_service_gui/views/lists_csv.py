"""Resource module for live resources."""
import logging
import os

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import EventsAdapter
from .utils import (
    check_login_open,
    get_event,
)


class ListsCSV(web.View):
    """Class representing the csv lists view."""

    async def get(self) -> web.Response:
        """Get route function that return the livelister page."""
        informasjon = ""
        html_template = "lists_csv.html"
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
            csv_files = await get_lists_csv(event_id)  # type: ignore

            if len(csv_files) == 0:
                informasjon = (
                    "Ingen filer er tilgjengelig. Vennligst prøv igjen senere."
                )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                html_template,
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "csv_files": csv_files,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")


async def get_lists_csv(event_id: str) -> list:
    """Get files available."""
    file_directory = EventsAdapter().get_global_setting("CSV_FILE_DIR")
    arr = os.listdir(file_directory)
    return arr
