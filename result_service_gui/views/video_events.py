"""Resource module for video_event resources."""
import logging

from aiohttp import web

from result_service_gui.services import (
    FotoService,
)
from .utils import (
    check_login,
    get_event,
)


class VideoEvents(web.View):
    """Class representing the video_event view."""

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        try:
            result = ""
            form = await self.request.post()
            event_id = str(form["event_id"])
            user = await check_login(self)
            event = await get_event(user, event_id)
            action = form['action']
            if action in ["pull_google"]:
                r = await FotoService().sync_photos_from_pubsub(user, event)
                result += f"  {r}<br>"
        except Exception as e:
            if "401" in str(e):
                result = "401 unathorized: Logg inn for å hente events."
            else:
                result = f"Det har oppstått en feil ved henting av video events. {e}"
            logging.error(f"Video events update - {e}")
        return web.Response(text=result)
