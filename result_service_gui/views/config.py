"""Resource module for main view."""

import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import ConfigAdapter
from .utils import check_login, get_event


class Config(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get function that return the index page."""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""

        try:
            user = await check_login(self)
            event = await get_event(user, event_id)

            try:
                event_config = await ConfigAdapter().get_all_configs(
                    user["token"], event
                )
            except Exception as e:
                event_config = []
                informasjon += f" Feil ved innlasting av config. {e}"
                logging.error(informasjon)

            return await aiohttp_jinja2.render_template_async(
                "config.html",
                self.request,
                {
                    "action": action,
                    "lopsinfo": "Admin: Målfoto",
                    "event": event,
                    "event_id": event_id,
                    "event_config": event_config,
                    "informasjon": informasjon,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to login page.")
            return web.HTTPSeeOther(location=f"/login?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates video events."""
        try:
            informasjon = ""
            form = await self.request.post()
            user = await check_login(self)
            event_id = str(form["event_id"])
            event = await get_event(user, event_id)

            if "reset_config" in form.keys():
                await ConfigAdapter().init_config(user["token"], event)
                informasjon = "Config er nullstilt."
            elif "update_one" in form.keys():
                key = form["key"]
                await ConfigAdapter().update_config(
                    user["token"], event, key, form["value"]  # type: ignore
                )
                informasjon = "Suksess. Informasjon er oppdatert."
        except Exception as e:
            informasjon = f"Det har oppstått en feil: {e}"
            logging.error(f"Config update - {e}")
        return web.HTTPSeeOther(
            location=f"/config?action=edit_mode&event_id={event_id}&informasjon={informasjon}"
        )
