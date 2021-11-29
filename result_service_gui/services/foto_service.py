"""Module for foto service."""
import datetime
import logging
from typing import Any, List

from .contestants_adapter import ContestantsAdapter
from .kjoreplan_service import KjoreplanService
from .raceclasses_adapter import RaceclassesAdapter
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

    async def get_foto_by_klasse(self, db: Any, lopsklasse: str, event: dict) -> List:
        """Get all foto for a given klasse."""
        foto = []
        cursor = db.foto_collection.find({"Løpsklasse": lopsklasse})
        for document in await cursor.to_list(length=500):
            foto.append(document)
            logging.debug(document)
        return foto

    async def get_foto_by_klubb(self, db: Any, klubb: str, event: dict) -> List:
        """Get all foto for a given klubb."""
        foto = []
        myquery = ".*" + klubb + ".*"
        cursor = db.foto_collection.find({"Klubb": {"$regex": myquery}})
        for document in await cursor.to_list(length=500):
            foto.append(document)
            logging.debug(document)
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
    db: Any,
    datetime_foto: str,
    raceduration: int,
    heat_index: str,
    event: dict,
) -> str:
    """Analyse photo tags and identify heat."""
    foundheat = ""
    racedate = event["date"]

    if datetime_foto is not None:
        heat = await KjoreplanService().get_heat_by_index(db, heat_index)
        if heat is not None:
            seconds = get_seconds_diff(datetime_foto, racedate + " " + heat["Start"])
            logging.debug(
                f"Verify heat, diff: {seconds}, heat: {racedate} {heat}, foto: {datetime_foto}"
            )
            if -300 < seconds < (300 + raceduration):
                logging.debug(f"Funnet heat: {heat}")
                foundheat = heat["Index"]

    return foundheat
