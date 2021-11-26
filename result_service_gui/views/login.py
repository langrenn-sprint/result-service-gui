"""Resource module for login view."""
import logging

from aiohttp import web
import aiohttp_jinja2
from aiohttp_session import get_session
from aiohttp_session import new_session

from result_service_gui.services import UserAdapter


class Login(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the index page."""
        username = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""

        try:
            create_new = False
            new = self.request.rel_url.query["new"]
            if new != "":
                session = await get_session(self.request)
                loggedin = UserAdapter().isloggedin(session)
                if loggedin:
                    create_new = True
                    username = session["username"]

        except Exception:
            create_new = False

        event = {"name": "Administrasjon", "organiser": "Ikke valgt"}

        return await aiohttp_jinja2.render_template_async(
            "login.html",
            self.request,
            {
                "lopsinfo": "Login",
                "event": event,
                "event_id": event_id,
                "informasjon": informasjon,
                "username": username,
                "create_new": create_new,
            },
        )

    async def post(self) -> web.Response:
        """Get route function that return the index page."""
        informasjon = ""
        result = 0
        logging.debug(f"Login: {self}")

        try:
            form = await self.request.post()
            try:
                event_id = self.request.rel_url.query["event_id"]
                logging.debug(f"Event: {event_id}")
            except Exception:
                event_id = ""

            # Perform login
            session = await new_session(self.request)
            result = await UserAdapter().login(
                str(form["username"]), str(form["password"]), session
            )
            if result != 200:
                informasjon = f"Innlogging feilet - {result}"

        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            result = 400

        event = {"name": "Langrenn", "organiser": "Ikke valgt"}
        if result != 200:
            return await aiohttp_jinja2.render_template_async(
                "login.html",
                self.request,
                {
                    "lopsinfo": "Login resultat",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                },
            )
        elif event_id != "":
            return web.HTTPSeeOther(
                location=f"/events?event={event_id}&informasjon={informasjon}"
            )
        else:
            return web.HTTPSeeOther(location=f"/?informasjon={informasjon}")
