"""Module for startliste service."""
import logging
from typing import Any, List


class StartListeService:
    """Class representing startliste service."""

    async def get_all_startlister(self, db: Any) -> List:
        """Get all startlister function."""
        startlister = []
        cursor = db.startliste_collection.find()
        for document in await cursor.to_list(length=100):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                startlister.append(document)
            logging.debug(document)
        return startlister

    async def get_startliste_by_klasse(self, db: Any, klasse: str) -> List:
        """Get all startlister function."""
        startlister = []
        cursor = db.startliste_collection.find({"Klasse": klasse})
        for document in await cursor.to_list(length=1000):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                startlister.append(document)
            logging.debug(document)
        return startlister

    async def get_startliste_by_lopsklasse(self, db: Any, klasse: str) -> List:
        """Get all startlister function."""
        startlister = []
        cursor = db.startliste_collection.find({"Løpsklasse": klasse})
        for document in await cursor.to_list(length=1000):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                startlister.append(document)
            logging.debug(document)
        return startlister

    async def create_startliste(self, db: Any, body: Any) -> int:
        """Create startliste function. After deletion of existing instances, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        if "startliste_collection" in collist:
            _heatliste: list = []
            for loper in body:
                if str(loper["Heat"]) not in _heatliste:
                    returncode = 202
                    result = await db.startliste_collection.delete_many(
                        {"Heat": str(loper["Heat"])}
                    )
                    logging.debug(result)
                    logging.debug(_heatliste)
                    _heatliste.append(str(loper["Heat"]))

        result = await db.startliste_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))
        return returncode

    async def get_startliste_by_heat(self, db: Any, heat: str) -> List:
        """Get startlister by startnumber function."""
        startlister = []
        cursor = db.startliste_collection.find({"Heat": heat})
        for document in await cursor.to_list(length=100):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                startlister.append(document)
        return startlister

    async def get_startliste_by_nr(self, db: Any, nr: str) -> List:
        """Get startlister by startnumber function."""
        startlister = []
        cursor = db.startliste_collection.find({"Nr": nr})
        for document in await cursor.to_list(length=100):
            startlister.append(document)
        return startlister
