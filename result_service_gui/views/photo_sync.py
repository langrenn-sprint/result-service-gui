"""Resource module for photo edit view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import FotoService, GooglePhotosAdapter
from .utils import (
    check_login_google_photos,
    get_event,
    get_local_time,
)


class PhotoSync(web.View):
    """Class representing the photo edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            album_id = self.request.rel_url.query["album_id"]
            album_title = self.request.rel_url.query["album_title"]
        except Exception:
            album_id = ""
            album_title = ""

        try:
            user = await check_login_google_photos(self)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            event = await get_event(user, event_id)
            all_albums = await GooglePhotosAdapter().get_albums(user["g_photos_token"])
            selected_album = await GooglePhotosAdapter().get_album_items(
                user["g_photos_token"], album_id
            )
            return await aiohttp_jinja2.render_template_async(
                "photo_sync.html",
                self.request,
                {
                    "lopsinfo": album_title,
                    "action": action,
                    "album": selected_album,
                    "album_id": album_id,
                    "all_albums": all_albums,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": get_local_time("HH:MM"),
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        user = await check_login_google_photos(self)

        informasjon = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        album_id = str(form["album_id"])
        album_title = str(form["album_title"])
        logging.debug(f"Form {form}")

        try:
            if "sync_from_google" in form.keys():
                event = await get_event(user, event_id)
                informasjon = await FotoService().sync_from_google(
                    user, event, album_id
                )
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        info = (
            f"album_id={album_id}&album_title={album_title}&informasjon={informasjon}"
        )
        return web.HTTPSeeOther(location=f"/photo_sync?event_id={event_id}&{info}")
