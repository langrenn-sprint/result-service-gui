"""Module for foto service."""
import datetime
import logging
import os
from typing import Any, List

from .contestants_adapter import ContestantsAdapter
from .google_photos_adapter import GooglePhotosAdapter
from .photos_adapter import PhotosAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .start_adapter import StartAdapter

klubber = [
    "Bækkelaget",
    "Heming",
    "Kjelsås",
    "Koll",
    "Lillomarka",
    "Lyn",
    "Njård",
    "Rustad",
    "Røa",
    "Try",
    "Årvoll",
]


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

    async def get_foto_by_klasse(
        self, user: dict, lopsklasse: str, event_id: str
    ) -> List:
        """Get all foto for a given klasse."""
        foto = []  # type: ignore
        return foto

    async def get_foto_by_klubb(self, user: dict, klubb: str, event_id: str) -> List:
        """Get all foto for a given klubb."""
        foto = []  # type: ignore
        return foto

    async def create_foto(self, token: str, db: Any, body: Any, event: dict) -> int:
        """Create foto function. Delete existing foto, if any."""
        returncode = 201

        # analyze tags and enrich with event information
        tags_fromnumbers = await find_event_information(db, token, body, event)
        body.update(tags_fromnumbers)
        if "Løpsklasse" not in body.keys():
            body["Løpsklasse"] = await find_lopsklasse(token, body, event["id"])
        logging.debug(body)

        result = await db.foto_collection.insert_one(body)
        logging.info(f"inserted one foto with id {result.inserted_id}")

        return returncode

    async def update_tags(self, db: Any, token: str, tags: Any, event: dict) -> None:
        """Update tags for one photo."""
        logging.debug(f"Got tags {tags} of type {type(tags)}")

        newvalues = {}
        for x, y in tags.items():
            if x == "OldNumbers":
                oldnumbers = y
            elif x == "Filename":
                myquery = {"Filename": y}

            else:
                newvalues[x] = y

        # enrich data
        nummere = tags["Numbers"]
        if oldnumbers != nummere:
            nummerliste = nummere.split(";")
            for nummer in nummerliste:
                tmp_tags = await find_info_from_startnummer(
                    db, token, nummer, tags["DateTime"], event
                )
                for x, y in tmp_tags.items():
                    logging.debug(f"Found tag: {x}, {y}")
                    if x not in newvalues.keys():
                        newvalues[x] = y
                    elif newvalues[x] == "":
                        newvalues[x] = y
                    elif y not in newvalues[x]:
                        newvalues[x] = newvalues[x] + ";" + y

        logging.debug(f"update tags {newvalues}")
        result = await db.foto_collection.update_one(myquery, {"$set": newvalues})
        logging.info(f"updated one {result}")

    async def sync_from_google(
        self,
        user: dict,
        event_id: str,
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
                photo["name"] = g_photo["filename"]
                photo["g_product_url"] = g_photo["productUrl"]
                photo["g_base_url"] = g_photo["baseUrl"]
                photo_id = await PhotosAdapter().update_photo(
                    user["token"], photo["id"], photo
                )
                logging.debug(f"Updated photo with id {photo_id}")
                i_u += 1
            except Exception:
                request_body = {
                    "name": g_photo["filename"],
                    "event_id": event_id,
                    "creation_time": format_zulu_time(creation_time),
                    "information": "",
                    "race_id": "",
                    "raceclass": "",
                    "biblist": [],
                    "clublist": [],
                    "g_id": g_photo["id"],
                    "g_product_url": g_photo["productUrl"],
                    "g_base_url": g_photo["baseUrl"],
                    "ai_text": [],
                    "ai_numbers": [],
                    "ai_information": "",
                }
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
def format_zulu_time(timez: str) -> str:
    """Convert from zulu time to normalized time - string formats."""
    # TODO: Move to properties
    pattern = "%Y-%m-%dT%H:%M:%SZ"
    TIME_ZONE_OFFSET_G_PHOTOS = os.getenv("TIME_ZONE_OFFSET_G_PHOTOS")
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


async def find_event_information(db: Any, token: str, tags: dict, event: dict) -> dict:
    """Analyse photo tags and identify event information."""
    personer = tags["Persons"]
    nummere = tags["Numbers"]
    newvalues = {"": ""}
    if personer.isnumeric():
        if int(personer) > 0:
            nummerliste = nummere.split(";")
            for nummer in nummerliste:
                tmp_tags = await find_info_from_startnummer(
                    db, token, nummer, tags["DateTime"], event
                )
                for x, y in tmp_tags.items():
                    logging.debug(f"Found tag: {x}, {y}")
                    if x not in newvalues.keys():
                        newvalues[x] = y
                    elif newvalues[x] == "":
                        newvalues[x] = y
                    elif y not in newvalues[x]:
                        newvalues[x] = newvalues[x] + ";" + y

            texts = tags["Texts"]
            liste = texts.split(";")
            for text in liste:
                if text in klubber:
                    if text not in newvalues["Klubb"]:
                        newvalues["Klubb"] = newvalues["Klubb"] + text + ";"
    return newvalues


async def find_info_from_startnummer(
    db: Any, token: str, startnummer: str, foto_time: str, event: dict
) -> dict:
    """Analyse photo tags and identify heat."""
    nye_tags = {}
    foundheat = ""
    funnetdeltaker = {}

    starter = await StartAdapter().get_startlist_by_bib(token, event["id"], startnummer)
    if len(starter) > 0:
        nye_tags["Numbers"] = startnummer
        for start in starter:
            # check startnummer
            logging.debug(f"Start funnet: {start}")
            # check heat (if not already found)
            if foundheat == "":
                foundheat = await verify_heat(
                    db, foto_time, event["date"], event["raceduration"], start["Heat"]
                )
                if foundheat != "":
                    nye_tags["Heat"] = foundheat
        # Get klubb and klasse
        funnetdeltaker = await ContestantsAdapter().get_contestant_by_bib(
            token, event["id"], startnummer
        )

    if "Startnr" in funnetdeltaker:
        nye_tags["Løpsklasse"] = funnetdeltaker["Løpsklasse"]
        nye_tags["Klubb"] = funnetdeltaker["Klubb"]

    return nye_tags


async def find_lopsklasse(token: str, tags: dict, event_id: str) -> str:
    """Analyse photo tags and identify løpsklasse."""
    funnetklasse = ""
    raceclasses = await RaceclassesAdapter().get_raceclasses(token, event_id)
    for klasse in raceclasses:
        logging.debug(klasse)
        if tags["Filename"].find(klasse["Løpsklasse"]) > -1:
            funnetklasse = klasse["Løpsklasse"]
            logging.debug(f"Found klasse: {funnetklasse}")

    return funnetklasse


async def verify_heat(
    token: str,
    datetime_foto: str,
    raceduration: int,
    race_id: str,
    event: dict,
) -> str:
    """Analyse photo tags and identify heat."""
    foundheat = ""
    racedate = event["date"]

    if datetime_foto is not None:
        heat = await RaceplansAdapter().get_race_by_id(token, race_id)
        if heat is not None:
            seconds = get_seconds_diff(datetime_foto, racedate + " " + heat["Start"])
            logging.debug(
                f"Verify heat, diff: {seconds}, heat: {racedate} {heat}, foto: {datetime_foto}"
            )
            if -300 < seconds < (300 + raceduration):
                logging.debug(f"Funnet heat: {heat}")
                foundheat = heat["Index"]

    return foundheat
