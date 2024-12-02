"""Resource module for photo update through ajax."""

import logging

from aiohttp import web

from result_service_gui.services import FotoService
from .utils import (
    check_login,
)


class PhotoUpdate(web.View):
    """Class representing the simple photo update service."""

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        result = "200"
        try:
            form = await self.request.post()
            action = form["action"]
            user = await check_login(self)
            photo_id = str(form["photo_id"])
            if action == "star_on":
                res = await FotoService().star_photo(user["token"], photo_id, True)
                logging.debug(f"Starred photo - {res}")
            elif action == "star_off":
                res = await FotoService().star_photo(user["token"], photo_id, False)
                logging.debug(f"Un-Starred photo - {res}")
        except Exception as e:
            result = f"Det har oppstått en feil: {e}"
            logging.error(f"Un-Starred photo - {e}")
        return web.Response(text=result)
