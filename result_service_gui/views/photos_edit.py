"""Resource module for photo edit view."""

import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    EventsAdapter,
    FotoService,
    PhotosAdapter,
    RaceclassesAdapter,
    RaceplansAdapter,
)
from .utils import (
    check_login,
    get_event,
)


class PhotosEdit(web.View):
    """Class representing the photos edit view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        try:
            filter = self.request.rel_url.query["filter"]
        except Exception:
            filter = ""
        try:
            valgt_klasse = self.request.rel_url.query["raceclass"]
        except Exception:
            valgt_klasse = ""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            user = await check_login(self)
        except Exception as e:
            return web.HTTPSeeOther(location=f"{e}")

        try:
            event = await get_event(user, event_id)
            if valgt_klasse:
                photos = await PhotosAdapter().get_photos_by_raceclass(
                    user["token"], event_id, valgt_klasse, False
                )
            else:
                photos = await PhotosAdapter().get_all_photos(
                    user["token"], event_id, False
                )
            if filter == "low_confidence":
                filtered_photos = []
                for photo in photos:
                    if photo["confidence"] < 51:
                        filtered_photos.append(photo)
                photos = filtered_photos
            photos.reverse()

            races = await RaceplansAdapter().get_all_races(user["token"], event_id)
            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            return await aiohttp_jinja2.render_template_async(
                "photos_edit.html",
                self.request,
                {
                    "lopsinfo": "Foto redigering",
                    "action": action,
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "local_time_now": EventsAdapter().get_local_time(event, "HH:MM"),
                    "photos": photos,
                    "raceclasses": raceclasses,
                    "races": races,
                    "valgt_klasse": valgt_klasse,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")

    async def post(self) -> web.Response:
        """Post route function that updates a collection of photos."""
        informasjon = ""
        form = await self.request.post()
        event_id = str(form["event_id"])
        user = await check_login(self)

        try:
            if "update_race_info" in form.keys():
                event = await get_event(user, event_id)
                informasjon = await FotoService().update_race_info(
                    user["token"], event, form  # type: ignore
                )
            elif "delete_all_local" in form.keys():
                informasjon = await FotoService().delete_all_local_photos(
                    user["token"], event_id
                )
            elif "delete_all_low_confidence" in form.keys():
                informasjon = await FotoService().delete_all_low_confidence_photos(
                    user["token"], event_id, 51
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
        except Exception as e:
            logging.error(f"Error: {e}")
            informasjon = f"Det har oppstått en feil - {e.args}."
            error_reason = str(e)
            if error_reason.startswith("401"):
                return web.HTTPSeeOther(
                    location=f"/login?informasjon=Ingen tilgang, vennligst logg inn på nytt. {e}"
                )

        return web.HTTPSeeOther(
            location=f"/photos_edit?event_id={event_id}&informasjon={informasjon}"
        )
