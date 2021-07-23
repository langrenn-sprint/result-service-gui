"""Module for resultatheat service."""
import logging
from typing import Any, List

from .kjoreplan_service import KjoreplanService


class ResultatHeatService:
    """Class representing resultatheat service."""

    async def get_all_resultatheat(self, db: Any) -> List:
        """Get all resultatheat function."""
        resultatheat = []
        cursor = db.resultatheat_collection.find()
        for document in await cursor.to_list(length=2000):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                resultatheat.append(document)
            logging.debug(document)
        return resultatheat

    async def get_resultatheat_by_klasse(self, db: Any, klasse: str) -> List:
        """Get all resultatheat function."""
        resultatheat = []
        cursor = db.resultatheat_collection.find({"Løpsklasse": klasse})
        for document in await cursor.to_list(length=1000):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                resultatheat.append(document)
            logging.debug(document)
        return resultatheat

    async def create_resultatheat(self, db: Any, body: Any) -> int:
        """Create resultatheat function. After deletion of existing instances, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        if "resultatheat_collection" in collist:
            _heatliste: list = []
            for resultat in body:
                if str(resultat["Heat"]) not in _heatliste:
                    returncode = 202
                    result = await db.resultatheat_collection.delete_many(
                        {"Heat": str(resultat["Heat"])}
                    )
                    logging.debug(result)
                    _heatliste.append(str(resultat["Heat"]))
            logging.debug(_heatliste)

        result = await db.resultatheat_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))

        """Update kjoreplan - register that heat is completed."""
        _heat = ""
        for loper in body:
            logging.debug(loper["Heat"])
            if (
                (_heat != loper["Heat"])
                and str(loper["Nr"]).isnumeric()
                and (int(loper["Nr"]) > 0)
            ):
                _heat = loper["Heat"]
                await KjoreplanService().update_registrer_resultat(db, _heat)
                logging.debug(_heat)

        return returncode

    async def get_resultatheat_by_heat(self, db: Any, heat: str) -> List:
        """Get one resultatheat by heat function."""
        resultatheat = []
        cursor = await db.resultatheat_collection.find({"Heat": heat})
        for document in await cursor.to_list(length=100):
            # filter out garbage and clean data
            if str(document["Nr"]).isnumeric() and (int(document["Nr"]) > 0):
                resultatheat.append(document)
            logging.debug(document)
        return resultatheat

    async def get_resultatheat_by_nr(self, db: Any, nr: str) -> List:
        """Get resultatheat by klasse function."""
        resultatheat = []
        cursor = db.resultatheat_collection.find({"Nr": nr})
        for document in await cursor.to_list(length=100):
            resultatheat.append(document)
            logging.debug(document)
        return resultatheat

    async def get_resultatheat_by_nr_and_heat(
        self, db: Any, nr: str, heat: str
    ) -> dict:
        """Get resultatheat by klasse function."""
        resultat = db.resultatheat_collection.find_one({"Nr": nr}, {"Heat": heat})
        logging.debug(resultat)
        return resultat
