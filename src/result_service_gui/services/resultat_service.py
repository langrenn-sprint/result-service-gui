"""Module for resultat service."""
import logging
from typing import Any, List


class ResultatService:
    """Class representing resultat service."""

    async def get_all_resultatlister(self, db: Any) -> List:
        """Get all resultatlister function."""
        resultatlister = []
        cursor = db.resultatliste_collection.find()
        for document in await cursor.to_list(length=2000):
            resultatlister.append(document)
            logging.debug(document)
        return resultatlister

    async def get_resultatliste_by_klasse(self, db: Any, klasse: str) -> List:
        """Get all resultatlister function."""
        resultatlister = []
        cursor = db.resultatliste_collection.find({"Klasse": klasse})
        for document in await cursor.to_list(length=1000):
            resultatlister.append(document)
            logging.debug(document)
        return resultatlister

    async def get_resultatliste_by_klubb(self, db: Any, klubb: str) -> List:
        """Get all resultatlister function."""
        resultatlister = []
        myquery = "^" + klubb
        cursor = db.resultatliste_collection.find({"Klubb": {"$regex": myquery}})
        for document in await cursor.to_list(length=1000):
            resultatlister.append(document)
            logging.debug(document)
        return resultatlister

    async def create_resultatliste(self, db: Any, body: Any) -> int:
        """Create resultatliste function. After deletion of existing instances, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        if "resultatliste_collection" in collist:
            _klasser: list = []
            for resultat in body:
                if str(resultat["Klasse"]) not in _klasser:
                    returncode = 202
                    result = await db.resultatliste_collection.delete_many(
                        {"Klasse": str(resultat["Klasse"])}
                    )
                    logging.debug(result)
                    logging.debug(_klasser)
                    _klasser.append(str(resultat["Klasse"]))

        """Create resultatlister function."""
        result = await db.resultatliste_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))
        return returncode

    async def get_resultatliste_by_heat(self, db: Any, heat: str) -> dict:
        """Get one resultatliste by heat function."""
        resultatliste = await db.resultatliste_collection.find({"Heat": heat})
        return resultatliste

    async def get_resultat_by_nr(self, db: Any, nr: str) -> List:
        """Get resultat by startnumber function."""
        resultatlister = []
        cursor = db.resultatliste_collection.find({"Nr": nr})
        for document in await cursor.to_list(length=100):
            resultatlister.append(document)
            logging.debug(document)
        return resultatlister
