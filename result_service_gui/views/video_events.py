"""Resource module for video_event resources."""

import json
import logging

from aiohttp import web

from result_service_gui.services import (
    ConfigAdapter,
    StatusAdapter,
)

from .utils import (
    check_login,
)


class VideoEvents(web.View):
    """Class representing the video_event view."""

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        response = {}
        try:
            user = await check_login(self)
            form = await self.request.post()
            event_id = str(form["event_id"])
            await check_login(self)
            action = form["action"]
            if action in ["status", "toggle"]:
                if "integration_start" in form:
                    await ConfigAdapter().update_config(
                        user["token"], event_id, "INTEGRATION_SERVICE_START", "True"
                    )
                elif "integration_stop" in form:
                    await ConfigAdapter().update_config(
                        user["token"], event_id, "INTEGRATION_SERVICE_START", "False"
                    )
                response["photo_queue_latest"] = await ConfigAdapter().get_config(
                    user["token"], event_id, "GOOGLE_LATEST_PHOTO"
                )
                response["informasjon"] = await get_integration_status(
                    user["token"], event_id
                )
        except Exception as e:
            if "401" in str(e):
                response["informasjon"] = (
                    "401 unathorized: Logg inn for å hente events."
                )
            else:
                response["informasjon"] = (
                    f"Det har oppstått en feil ved henting av video events. {e}"
                )
            logging.exception("Video events update")
        json_response = json.dumps(response)
        return web.Response(body=json_response)


async def get_integration_status(token: str, event_id: str) -> str:
    """Get video analytics status messages."""
    response = ""
    result_list = await StatusAdapter().get_status(token, event_id, 10)
    for res in result_list:
        info_time = f"<a title={res['time']}>{res['time'][-8:]}</a>"
        response += f"{info_time} - {res['message']}<br>"
    return response
