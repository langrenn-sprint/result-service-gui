"""Module for foto service."""

import datetime
import json
import logging
import os

from .albums_adapter import AlbumsAdapter
from .config_adapter import ConfigAdapter
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .google_pub_sub_adapter import GooglePubSubAdapter
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
        return "Alle bilder er slettet."

    async def delete_all_local_photos(self, token: str, event_id: str) -> str:
        """Delete all local copies of photo information."""
        photos = await PhotosAdapter().get_all_photos(token, event_id, False)
        for photo in photos:
            result = await PhotosAdapter().delete_photo(token, photo["id"])
            logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return "Alle bilder er slettet."

    async def delete_all_low_confidence_photos(
        self, token: str, event_id: str, limit: int
    ) -> str:
        """Delete all local copies of photo where confidence is below photo."""
        photos = await PhotosAdapter().get_all_photos(token, event_id, False)
        i = 0
        for photo in photos:
            if photo["confidence"] < limit:
                result = await PhotosAdapter().delete_photo(token, photo["id"])
                i += 1
                logging.debug(f"Deleted photo with id {photo['id']}, result {result}")
        return f"{i} bilder med confidence under {limit} er slettet."

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

    async def update_race_info(self, token: str, event: dict, form: dict) -> str:
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
                        raceclasses = await RaceclassesAdapter().get_raceclasses(
                            token, event["id"]
                        )
                        photo = await PhotosAdapter().get_photo(token, photo_id)
                        photo["biblist"] = []
                        photo["clublist"] = []

                        # try to identify race information
                        message = {
                            "ai_crop_numbers": json.loads(new_biblist),
                            "ai_numbers": [],
                        }
                        result = await link_ai_info_to_photo(
                            token, photo, message, event, raceclasses
                        )

                        result = await PhotosAdapter().update_photo(
                            token, photo["id"], photo
                        )
                        icount += 1
                        logging.debug(
                            f"Updated photo with id {photo_id} for event {event['name']} - {result}"
                        )
                except Exception as e:
                    logging.error(f"Error reading biblist - {form[key]}: {e}")
                    informasjon += "En Feil oppstod. "
            elif key.startswith("race_id_"):
                new_race_id = form[key]
                photo_id = key[8:]
                old_race_id = form[f"old_race_id_{photo_id}"]
                if new_race_id != old_race_id:
                    photo = await PhotosAdapter().get_photo(token, photo_id)
                    photo["race_id"] = new_race_id
                    if new_race_id:
                        photo["raceclass"] = form[f"raceclass_{new_race_id}"]
                    else:
                        photo["raceclass"] = ""
                    result = await PhotosAdapter().update_photo(
                        token, photo["id"], photo
                    )
                    icount += 1
                    logging.debug(
                        f"Updated photo with id {photo_id} for event {event['name']} - {result}"
                    )
        informasjon = f"Utført {icount} oppdateringer."
        return informasjon

    async def sync_photos_from_pubsub(
        self,
        user: dict,
        event: dict,
    ) -> str:
        """Get events from pubsub and sync with local database."""
        informasjon = ""
        i_c = 0
        i_u = 0
        i_other = 0
        # get all messages from pubsub

        pull_messages = await GooglePubSubAdapter().pull_messages()
        if len(pull_messages) == 0:
            informasjon = "Ingen bilder funnet."
        else:
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
                        photo["g_crop_url"] = ""
                        photo["g_base_url"] = message["photo_url"]
                        if message["photo_info"]["passeringspunkt"] in [
                            "Finish",
                            "Mål",
                        ]:
                            photo["is_photo_finish"] = True
                        if message["photo_info"]["passeringspunkt"] == "Start":
                            photo["is_start_registration"] = True
                        result = await PhotosAdapter().update_photo(
                            user["token"], photo["id"], photo
                        )
                        logging.debug(
                            f"Updated photo with id {photo['id']}, result {result}"
                        )
                        i_u += 1
                    else:
                        # create new photo
                        photo_info = {
                            "confidence": 0,
                            "name": os.path.basename(message["photo_url"]),
                            "is_photo_finish": False,
                            "is_start_registration": False,
                            "starred": False,
                            "event_id": event["id"],
                            "creation_time": format_time(creation_time, False),
                            "ai_information": message["ai_information"],
                            "information": message["photo_info"],
                            "race_id": "",
                            "raceclass": "",
                            "biblist": [],
                            "clublist": [],
                            "g_crop_url": message["crop_url"],
                            "g_base_url": message["photo_url"],
                        }
                        # new photo - try to link with event activities
                        if message["photo_info"]["passeringspunkt"] in [
                            "Finish",
                            "Mål",
                        ]:
                            photo_info["is_photo_finish"] = True
                        if message["photo_info"]["passeringspunkt"] == "Start":
                            photo_info["is_start_registration"] = True
                        if message["ai_information"]:
                            result = await link_ai_info_to_photo(
                                user["token"],
                                photo_info,
                                message["ai_information"],
                                event,
                                raceclasses,
                            )

                        photo_id = await PhotosAdapter().create_photo(
                            user["token"], photo_info
                        )
                        logging.debug(f"Created photo with id {photo_id} - {result}")
                        i_c += 1
                else:
                    i_other += 1
            informasjon = (
                f"Synkronisert bilder fra PubSub. {i_u} oppdatert og {i_c} opprettet."
            )
            if i_other > 0:
                informasjon += f" Forkastet {i_other} meldinger som ikke tilhører dette arrangementet."
        return informasjon


async def link_ai_info_to_photo(
    token: str, photo_info: dict, ai_information: dict, event: dict, raceclasses: list
) -> int:
    """Link ai information to photo."""
    # first check for bib on cropped image
    result = 204
    for nummer in ai_information["ai_crop_numbers"]:
        result = await find_race_info_by_bib(
            token, nummer, photo_info, event, raceclasses, 100
        )
    # use time only if by bib was not successful
    if result == 204:
        result = await find_race_info_by_time(token, photo_info, event, 50)
    return result


async def find_race_info_by_bib(
    token: str,
    bib: int,
    photo_info: dict,
    event: dict,
    raceclasses: list,
    confidence: int,
) -> int:
    """Analyse photo ai info and add race info to photo."""
    result = 204  # no content
    foundheat = ""
    raceduration = await ConfigAdapter().get_config_int(
        token, event, "RACE_DURATION_ESTIMATE"
    )
    starter = await StartAdapter().get_start_entries_by_bib(token, event["id"], bib)
    if len(starter) > 0:
        for start in starter:
            # check heat (if not already found)
            if foundheat == "":
                foundheat = await verify_heat_time(
                    token,
                    event,
                    photo_info["creation_time"],
                    raceduration,
                    start["race_id"],
                )
                if foundheat != "":
                    photo_info["race_id"] = foundheat
                    result = 200  # OK, found a heat

                    # Get klubb and klasse
                    if bib not in photo_info["biblist"]:
                        try:
                            contestant = (
                                await ContestantsAdapter().get_contestant_by_bib(
                                    token, event["id"], bib
                                )
                            )
                            if contestant:
                                photo_info["biblist"].append(bib)
                                if contestant["club"] not in photo_info["clublist"]:
                                    photo_info["clublist"].append(contestant["club"])
                                photo_info["raceclass"] = find_raceclass(
                                    contestant["ageclass"], raceclasses
                                )
                                photo_info["confidence"] = (
                                    confidence  # identified by bib - high confidence!
                                )
                        except Exception as e:
                            logging.debug(f"Missing attribute - {e}")
                            result = 206  # Partial content
    return result


async def find_race_info_by_time(
    token: str, photo_info: dict, event: dict, confidence: int
) -> int:
    """Analyse photo time and identify race with best time-match."""
    result = 204  # no content
    raceduration = await ConfigAdapter().get_config_int(
        token, event, "RACE_DURATION_ESTIMATE"
    )
    all_races = await RaceplansAdapter().get_all_races(token, event["id"])
    best_fit_race = {
        "race_id": "",
        "seconds_diff": 10000,
        "raceclass": "",
    }
    for race in all_races:
        seconds_diff = abs(
            get_seconds_diff(photo_info["creation_time"], race["start_time"])
            - raceduration
        )

        if seconds_diff < best_fit_race["seconds_diff"]:  # type: ignore
            best_fit_race["seconds_diff"] = seconds_diff
            best_fit_race["race_id"] = race["id"]
            best_fit_race["raceclass"] = race["raceclass"]
            best_fit_race["name"] = f"{race['round']}{race['index']}{race['heat']}"

    if best_fit_race["seconds_diff"] < 10000:  # type: ignore
        photo_info["race_id"] = best_fit_race["race_id"]
        photo_info["raceclass"] = best_fit_race["raceclass"]
        result = 200  # OK, found a heat
        photo_info["confidence"] = confidence  # identified by time - medium confidence!
        logging.info(f"Diff - best match race {best_fit_race}")
    return result


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
    date_patterns = EventsAdapter().get_global_setting("DATE_PATTERNS")
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

    date_patterns = EventsAdapter().get_global_setting("DATE_PATTERNS")
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
    event: dict,
    datetime_foto: str,
    raceduration: int,
    race_id: str,
) -> str:
    """Analyse photo tags and identify heat."""
    foundheat = ""
    if datetime_foto is not None:
        race = await RaceplansAdapter().get_race_by_id(token, race_id)
        if race is not None:
            max_time_dev = await ConfigAdapter().get_config_int(
                token, event, "RACE_TIME_DEVIATION_ALLOWED"
            )
            seconds = get_seconds_diff(datetime_foto, race["start_time"])
            if 0 < seconds < (max_time_dev + raceduration):
                foundheat = race["id"]
                race_name = (
                    f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}"
                )
                logging.info(
                    f"Diff - confirmed bib {seconds} seconds, for race {race_name}"
                )

    return foundheat
