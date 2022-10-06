"""Resource module for photo edit view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import AlbumsAdapter, FotoService, GooglePhotosAdapter
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
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        try:
            user = await check_login_google_photos(self, event_id)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            event = await get_event(user, event_id)
            # check if automatic sync is active
            try:
                if action in ["auto_sync", "one_sync"]:
                    informasjon += await FotoService().sync_photos_from_google(
                        user, event
                    )
            except Exception as e:
                informasjon = f"Det har oppstått en feil ved synkronisering. {e}"
                action = ""
            synced_albums = await AlbumsAdapter().get_all_albums(user["token"], event_id)
            g_albums = await GooglePhotosAdapter().get_albums(user["g_photos_token"])
            return await aiohttp_jinja2.render_template_async(
                "photo_sync.html",
                self.request,
                {
                    "lopsinfo": "",
                    "action": action,
                    "g_albums": g_albums,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": get_local_time("HH:MM"),
                    "synced_albums": synced_albums,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of klasses."""
        action = ""
        informasjon = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        user = await check_login_google_photos(self, event_id)
        event = await get_event(user, event_id)
        album_id = str(form["album_id"])
        album_title = str(form["album_title"])
        logging.debug(f"Form {form}")

        try:
            if "sync_from_google" in form.keys():
                # the actual sync is done on get-processing
                try:
                    action = str(form["action"])
                    if action == "auto_sync":
                        informasjon = f"Automatisk synkronisering er på. Siden oppdateres hvert minutt. {informasjon}"
                except Exception:
                    action = "one_sync"
            elif "add_photo_finish" in form.keys():
                album = await AlbumsAdapter().get_album(user["token"], album_id)
                album["is_photo_finish"] = True
                resU = await AlbumsAdapter().update_album(user["token"], album["id"], album)
                informasjon = f"Album {album_title} er registrert som photo_finish ({resU})"
            elif "add_sync" in form.keys():
                resA = await FotoService().add_album_for_synk(
                    user["token"],
                    user["g_photos_token"],
                    event,
                    album_id
                )
                informasjon = f"Album {album_title} er lagt til synkronisering ({resA})"
            elif "delete_all_local" in form.keys():
                informasjon = await FotoService().delete_all_local_albums(
                    user["token"], event_id
                )
            elif "stop_sync" in form.keys():
                resD = await AlbumsAdapter().delete_album(user["token"], album_id)
                informasjon = f"Album {album_title} er fjernet fra synkronisering ({resD})"
                album_id = ""
                album_title = ""
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
        return web.HTTPSeeOther(location=f"/photo_sync?event_id={event_id}&{info}&action={action}")
