"""Module for foto service."""
import datetime
import json
import logging
import os

from .albums_adapter import AlbumsAdapter
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .photos_adapter import PhotosAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .start_adapter import StartAdapter


class FotoService:
    """Class representing foto service."""

    async def delete_all_local_albums(self, token: str, event_id: str) -> str:
        """Delete all local copies of album sync information."""
        albums = await AlbumsAdapter().get_all_albums(token, event_id)
        for album in albums:
            result = await AlbumsAdapter().delete_album(token, album.id)
            logging.debug(f"Deleted album with id {album.id}, result {result}")
        return "Alle lokale kopier er slettet."

    async def delete_all_local_photos(self, token: str, event_id: str) -> str:
        """Delete all local copies of photo information."""
        photos = await PhotosAdapter().get_all_photos(token, event_id, False)
        for photo in photos:
            result = await PhotosAdapter().delete_photo(token, photo["id"])
            logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return "Alle lokale kopier er slettet."

    async def star_photo(self, token: str, photo_id: str, starred: bool) -> str:
        """Mark photo as starred, or unstarr."""
        informasjon = ""
        photo = await PhotosAdapter().get_photo(token, photo_id)
        photo["starred"] = starred
        result = await PhotosAdapter().update_photo(token, photo["id"], photo)
        logging.debug(f"Updated photo with id {photo_id} - {result}")
        if starred:
            informasjon = "Foto er stjernemerket."
        else:
            informasjon = "Stjernemerke fjernet."
        return informasjon

    async def update_race_info(self, token: str, event_id: str, form: dict) -> str:
        """Update race information in phostos, biblist."""
        informasjon = ""
        icount = 0
        for key in form.keys():
            if key.startswith("biblist_"):
                try:
                    new_biblist = form[key]
                    photo_id = key[8:]
                    old_biblist = form[f"old_biblist_{photo_id}"]
                    if new_biblist != old_biblist:
                        photo = await PhotosAdapter().get_photo(token, photo_id)
                        photo["biblist"] = json.loads(new_biblist)
                        result = await PhotosAdapter().update_photo(
                            token, photo["id"], photo
                        )
                        icount += 1
                        logging.debug(f"Updated photo with id {photo_id} for event {event_id} - {result}")
                except Exception as e:
                    logging.error(f"Error reading biblist - {form[key]}: {e}")
                    informasjon += "En Feil oppstod. "
        informasjon = f"Oppdatert {icount} bilder."
        return informasjon

    async def sync_photos_from_pubsub(
        self,
        user: dict,
        event: dict,
        pull_messages: list,
    ) -> str:
        """Get events from pubsub and sync with local database."""
        informasjon = ""
        i_c = 0
        i_u = 0
        raceclasses = await RaceclassesAdapter().get_raceclasses(
            user["token"], event["id"]
        )
        for message in pull_messages:
            # use message data to identify contestant/bib and race
            # then create photo
            # check if message event_id is same as event_id
            if message["event_id"] == event["id"]:
                try:
                    creation_time = message["photo_info"]["passeringstid"]
                except Exception:
                    creation_time = ""
                # update or create record in db
                try:
                    photo = await PhotosAdapter().get_photo_by_g_base_url(
                        user["token"], message["photo_url"]
                    )
                except Exception:
                    photo = {}
                if photo:
                    # update existing photo
                    photo["name"] = os.path.basename(message["photo_url"])
                    photo["g_product_url"] = ""
                    photo["g_base_url"] = message["photo_url"]
                    if message["photo_info"]["passeringspunkt"] in ["Finish", "Mål"]:
                        photo["is_photo_finish"] = True
                    if message["photo_info"]["passeringspunkt"] == "Start":
                        photo["is_start_registration"] = True
                    photo_id = await PhotosAdapter().update_photo(
                        user["token"], photo["id"], photo
                    )
                    logging.debug(f"Updated photo with id {photo_id}")
                    i_u += 1
                else:
                    # create new photo
                    request_body = {
                        "name": os.path.basename(message["photo_url"]),
                        "is_photo_finish": False,
                        "is_start_registration": False,
                        "starred": False,
                        "event_id": event["id"],
                        "creation_time": format_time(creation_time, False),
                        "ai_information": message["ai_information"],
                        "information": message['photo_info'],
                        "race_id": "",
                        "raceclass": "",
                        "biblist": [],
                        "clublist": [],
                        "g_id": "",
                        "g_product_url": message["crop_url"],
                        "g_base_url": message["photo_url"],
                    }
                    # new photo - try to link with event activities
                    if message["photo_info"]["passeringspunkt"] in ["Finish", "Mål"]:
                        request_body["is_photo_finish"] = True
                    if message["photo_info"]["passeringspunkt"] == "Start":
                        request_body["is_start_registration"] = True
                    if message["ai_information"]:
                        for nummer in message["ai_information"]["ai_numbers"]:
                            result = await find_race_info_from_bib(user["token"], nummer, request_body, event, raceclasses)
                            logging.debug(f"Link to race info, result {result}")
                    photo_id = await PhotosAdapter().create_photo(
                        user["token"], request_body
                    )
                    logging.debug(f"Created photo with id {photo_id}")
                    i_c += 1
        informasjon = f"Synkronisert bilder fra PubSub. {i_u} oppdatert og {i_c} opprettet."
        return informasjon


# internal functions
async def get_link_to_event_info_from_ai(token: str, photo: dict, event: dict, raceclasses: list) -> int:
    """Use information from AI to link photo to the event activities."""
    result = 200
    ai_information = photo["ai_information"]
    if ai_information["ai_numbers"]:
        for nummer in ai_information["ai_numbers"]:
            result = await find_race_info_from_bib(token, nummer, photo, event, raceclasses)
    return result


async def find_race_info_from_bib(
    token: str, bib: int, photo: dict, event: dict, raceclasses: list
) -> int:
    """Analyse photo ai info and add race info to photo."""
    foundheat = ""
    raceduration = int(EventsAdapter().get_global_setting("RACE_DURATION_ESTIMATE"))
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
                                photo["raceclass"] = find_raceclass(contestant["ageclass"], raceclasses)
                        except Exception as e:
                            logging.debug(f"Missing attribute - {e}")

    return 200


def find_raceclass(ageclass: str, raceclasses: list) -> str:
    """Analyse photo tags and identify løpsklasse."""
    funnetklasse = ""
    for klasse in raceclasses:
        if ageclass in klasse["ageclasses"]:
            funnetklasse = klasse["name"]
            break

    return funnetklasse


def format_time(timez: str, zulu: bool) -> str:
    """Convert to normalized time - string formats."""
    t2 = None
    time_zone_offset_g_photos = EventsAdapter().get_global_setting(
        "TIME_ZONE_OFFSET_G_PHOTOS"
    )
    date_patterns = EventsAdapter().get_global_setting(
        "DATE_PATTERNS"
    )
    date_pattern_list = date_patterns.split(";")
    for pattern in date_pattern_list:
        try:
            t1 = datetime.datetime.strptime(timez, pattern)
            # calculate new time
            delta_seconds = int(time_zone_offset_g_photos) * 3600  # type: ignore
            if zulu:
                t2 = t1 + datetime.timedelta(seconds=delta_seconds)
            else:
                t2 = t1
            break
        except ValueError:
            logging.debug(f"Got error parsing time {ValueError}")
    if t2:
        time = f"{t2.strftime('%Y')}-{t2.strftime('%m')}-{t2.strftime('%d')}T{t2.strftime('%X')}"
    else:
        time = ""
    return time


def get_seconds_diff(time1: str, time2: str) -> int:
    """Compare time1 and time2, return time diff in min."""
    t1 = datetime.datetime.strptime("1", "%S")  # nitialize time to zero
    t2 = datetime.datetime.strptime("1", "%S")

    date_patterns = EventsAdapter().get_global_setting(
        "DATE_PATTERNS"
    )
    date_pattern_list = date_patterns.split(";")
    for pattern in date_pattern_list:
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
    max_time_dev = int(EventsAdapter().get_global_setting("RACE_TIME_DEVIATION_ALLOWED"))

    if datetime_foto is not None:
        race = await RaceplansAdapter().get_race_by_id(token, race_id)
        if race is not None:
            seconds = get_seconds_diff(datetime_foto, race["start_time"])
            if -max_time_dev < seconds < (max_time_dev + raceduration):
                foundheat = race["id"]

    return foundheat
