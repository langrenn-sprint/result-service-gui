"""Resource module for photo edit view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import FotoService, PhotosAdapter
from .utils import (
    check_login_google_photos,
    get_event,
    get_local_time,
)


class PhotoEdit(web.View):
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
            user = await check_login_google_photos(self)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            event = await get_event(user, event_id)
            photos = await PhotosAdapter().get_all_photos(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "photo_edit.html",
                self.request,
                {
                    "lopsinfo": "Foto redigering",
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": get_local_time("HH:MM"),
                    "photos": photos,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        user = await check_login_google_photos(self)

        informasjon = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        logging.debug(f"Form {form}")

        try:
            if "update_race_info" in form.keys():
                informasjon = await FotoService().update_race_info(
                    user["token"], event_id, form  # type: ignore
                )
            elif "delete_all_local" in form.keys():
                informasjon = await FotoService().delete_all_local_photos(
                    user["token"], event_id
                )
            elif "delete_select" in form.keys():
                informasjon = "Sletting utført: "
                for key in form.keys():
                    if key.startswith("update_"):
                        photo_id = str(form[key])
                        result = await PhotosAdapter().delete_photo(
                            user["token"], photo_id
                        )
                        logging.debug(f"Deleted photo - {result}")
                        informasjon += f"{key} "
            elif "star_photo" in form.keys():
                informasjon = "Oppdatert stjernemarkering utført: "
                for key in form.keys():
                    if key.startswith("update_"):
                        photo_id = str(form[key])
                        res = await FotoService().star_photo(
                            user["token"], photo_id, True
                        )
                        logging.debug(f"Starred photo - {res}")
                        informasjon += f"{key} "
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(
            location=f"/photo_edit?event_id={event_id}&informasjon={informasjon}"
        )
