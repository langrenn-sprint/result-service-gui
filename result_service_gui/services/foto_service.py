"""Module for foto service."""
import datetime
import logging
from typing import Any, List

from .ai_image_service import AiImageService
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .google_photos_adapter import GooglePhotosAdapter
from .photos_adapter import PhotosAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .start_adapter import StartAdapter


class FotoService:
    """Class representing foto service."""

    async def get_all_foto(self, db: Any, event: dict) -> List:
        """Get all foto function."""
        foto = []
        cursor = db.foto_collection.find()
        for document in await cursor.to_list(length=2000):
            foto.append(document)
            logging.debug(document)
        return foto

    async def get_photo_by_raceclass(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
        """Get all foto for a given klasse."""
        photos = []
        tmp_photos = await PhotosAdapter().get_all_photos(token, event_id)
        for photo in tmp_photos:
            if raceclass in photo["raceclass"]:
                photos.append(photo)
        return photos

    async def delete_all_local_photos(self, token: str, event_id: str) -> str:
        """Delete all local copies of photo information."""
        photos = await PhotosAdapter().get_all_photos(token, event_id)
        for photo in photos:
            result = await PhotosAdapter().delete_photo(token, photo["id"])
            logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return "Alle lokale kopier er slettet."

    async def sync_from_google(
        self,
        user: dict,
        event: dict,
        album_id: str,
    ) -> str:
        """Get photos from google and sync with local database."""
        informasjon = ""
        album = await GooglePhotosAdapter().get_album_items(
            user["g_photos_token"], album_id
        )
        i_c = 0
        i_u = 0
        for g_photo in album["mediaItems"]:  # type: ignore
            creation_time = g_photo["mediaMetadata"]["creationTime"]
            # update or create record in db
            try:
                photo = await PhotosAdapter().get_photo_by_g_id(
                    user["token"], g_photo["id"]
                )
            except Exception:
                photo = {}

            if photo:
                # update existing photo
                photo["name"] = g_photo["filename"]
                photo["g_product_url"] = g_photo["productUrl"]
                photo["g_base_url"] = g_photo["baseUrl"]

                photo_id = await PhotosAdapter().update_photo(
                    user["token"], photo["id"], photo
                )
                logging.debug(f"Created photo with id {photo_id}")
                i_u += 1
            else:
                # create new photo
                request_body = {
                    "name": g_photo["filename"],
                    "event_id": event["id"],
                    "creation_time": format_zulu_time(creation_time),
                    "information": "",
                    "race_id": "",
                    "raceclass": "",
                    "biblist": [],
                    "clublist": [],
                    "g_id": g_photo["id"],
                    "g_product_url": g_photo["productUrl"],
                    "g_base_url": g_photo["baseUrl"],
                }

                # new photo - analyze content
                request_body[
                    "ai_information"
                ] = AiImageService().analyze_photo_with_google_for_langrenn(
                    f"{g_photo['baseUrl']}=w800-h800"
                )

                # new photo - try to link with event activities
                result = await get_link_to_event_info_from_ai(
                    user["token"], request_body, event
                )
                logging.debug(f"Link to race info, result {result}")
                photo_id = await PhotosAdapter().create_photo(
                    user["token"], request_body
                )
                logging.debug(f"Created photo with id {photo_id}")
                i_c += 1

        informasjon = (
            f"Synkronisert bilder fra Google. {i_u} oppdatert og {i_c} opprettet."
        )
        return informasjon


# internal functions
async def get_link_to_event_info_from_ai(token: str, photo: dict, event: dict) -> int:
    """Use information from AI to link photo to the event activities."""
    result = 200
    ai_information = photo["ai_information"]
    if ai_information["ai_numbers"]:
        for nummer in ai_information["ai_numbers"]:
            result = await find_race_info_from_bib(token, nummer, photo, event)
    return result


async def find_race_info_from_bib(
    token: str, bib: int, photo: dict, event: dict
) -> int:
    """Analyse photo ai info and add race info to photo."""
    foundheat = ""
    raceduration = 200  # TODO: move race duration to propert file
    starter = await StartAdapter().get_start_entries_by_bib(token, event["id"], bib)
    if len(starter) > 0:
        for start in starter:
            # check heat (if not already found)
            if foundheat == "":
                foundheat = await verify_heat_time(
                    token,
                    photo["creation_time"],
                    raceduration,
                    start["race_id"],
                )
                if foundheat != "":
                    photo["race_id"] = foundheat
                    # Get klubb and klasse
                    if bib not in photo["biblist"]:
                        try:
                            contestant = (
                                await ContestantsAdapter().get_contestant_by_bib(
                                    token, event["id"], bib
                                )
                            )
                            if contestant:
                                photo["biblist"].append(bib)
                                if contestant["club"] not in photo["clublist"]:
                                    photo["clublist"].append(contestant["club"])
                                photo["raceclass"] = contestant["ageclass"]
                        except Exception as e:
                            logging.debug(f"Missing attribute - {e}")

    return 200


async def find_lopsklasse(token: str, tags: dict, event_id: str) -> str:
    """Analyse photo tags and identify l??psklasse."""
    funnetklasse = ""
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    for klasse in raceclasses:
        logging.debug(klasse)
        if tags["Filename"].find(klasse["L??psklasse"]) > -1:
            funnetklasse = klasse["L??psklasse"]
            logging.debug(f"Found klasse: {funnetklasse}")

    return funnetklasse


def format_zulu_time(timez: str) -> str:
    """Convert from zulu time to normalized time - string formats."""
    # TODO: Move to properties
    pattern = "%Y-%m-%dT%H:%M:%SZ"
    TIME_ZONE_OFFSET_G_PHOTOS = EventsAdapter().get_global_setting(
        "TIME_ZONE_OFFSET_G_PHOTOS"
    )
    try:
        t1 = datetime.datetime.strptime(timez, pattern)
        # calculate new time
        delta_seconds = int(TIME_ZONE_OFFSET_G_PHOTOS) * 3600  # type: ignore
        t2 = t1 + datetime.timedelta(seconds=delta_seconds)
    except ValueError:
        logging.debug(f"Got error parsing time {ValueError}")
        return ""

    time = f"{t2.strftime('%Y')}-{t2.strftime('%m')}-{t2.strftime('%d')}T{t2.strftime('%X')}"
    return time


def get_seconds_diff(time1: str, time2: str) -> int:
    """Compare time1 and time2, return time diff in min."""
    seconds_diff = 1000
    t1 = datetime.datetime.strptime("1", "%S")  # nitialize time to zero
    t2 = datetime.datetime.strptime("1", "%S")
    # TODO: Move to properties
    date_patterns = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y:%m:%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%Y%m%d %H:%M:%S",
    ]
    for pattern in date_patterns:
        try:
            t1 = datetime.datetime.strptime(time1, pattern)
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")
            pass
        try:
            t2 = datetime.datetime.strptime(time2, pattern)
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")
            pass

    seconds_diff = int((t1 - t2).total_seconds())

    return seconds_diff


async def verify_heat_time(
    token: str,
    datetime_foto: str,
    raceduration: int,
    race_id: str,
) -> str:
    """Analyse photo tags and identify heat."""
    foundheat = ""

    if datetime_foto is not None:
        race = await RaceplansAdapter().get_race_by_id(token, race_id)
        if race is not None:
            seconds = get_seconds_diff(datetime_foto, race["start_time"])
            if -300 < seconds < (300 + raceduration):
                foundheat = race["id"]

    return foundheat
