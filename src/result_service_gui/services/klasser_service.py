"""Module for klasser service."""
import logging
from typing import Any, List


class KlasserService:
    """Class representing klasser service."""

    async def get_all_klasser(self, db: Any) -> List:
        """Get all klasser function."""
        klasser = []
        cursor = db.klasser_collection.find()
        for document in await cursor.to_list(length=100):
            klasser.append(document)
            logging.debug(document)
        return klasser

    async def create_klasser(self, db: Any, body: Any) -> int:
        """Create klasser function. After deletion of existing instances, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        # delete old instances
        if "klasser_collection" in collist:
            returncode = 202
            result = await db.klasser_collection.delete_many({})
            logging.debug(result)

        # insert new
        result = await db.klasser_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))

        # update tidplan if kjøreplan exists
        if "kjoreplan_collection" in collist:
            await KlasserService().update_tidplan(db)
            logging.debug("Updating tidplan")

        return returncode

    async def get_klasse(self, db: Any, klasse: str) -> dict:
        """Get one klass by klasse function."""
        result = await db.klasser_collection.find_one({"Klasse": klasse})
        return result

    async def get_klasse_by_lopsklasse(self, db: Any, klasse: str) -> dict:
        """Get klasser in same lopsklasse function."""
        result = await db.klasser_collection.find_one({"Løpsklasse": klasse})
        return result

    async def get_lopsklasse_for_klasse(self, db: Any, klasse: str) -> str:
        """Get one klass by klasse function."""
        result = await db.klasser_collection.find_one({"Klasse": klasse})
        return result["Løpsklasse"]

    # TODO: reduser kompleksistet i denne funksjonen
    async def update_tidplan(self, db: Any) -> int:  # noqa: C901
        """Update tidplan function. Will update klasser object, requires Kjøreplan created."""
        returncode = 201

        # get klasser
        klasser = []
        cursor = db.klasser_collection.find()
        for document in await cursor.to_list(length=100):
            klasser.append(document)

        # get heat
        kjoreplan = []
        cursor = db.kjoreplan_collection.find()
        for document in await cursor.to_list(length=500):
            kjoreplan.append(document)

        # loop through klasser and kjøreplan - update start time pr round
        for klasse in klasser:
            klasse["SemiC"] = False
            klasse["FinaleC"] = False
            klasse["FinaleB"] = False
            _myquery = {"Klasse": klasse["Klasse"]}
            for heat in kjoreplan:
                if klasse["Løpsklasse"] == heat["Løpsklasse"]:
                    if heat["Heat"] == "KA1":
                        _newvalue = {"TidKvart": heat["Start"]}
                        result = await db.klasser_collection.update_one(
                            _myquery, {"$set": _newvalue}
                        )
                        logging.debug(result)
                        returncode = 202
                    elif heat["Heat"] == "SC1":
                        _newvalue = {"TidSemi": heat["Start"]}
                        result = await db.klasser_collection.update_one(
                            _myquery, {"$set": _newvalue}
                        )
                        logging.debug(result)
                        klasse["SemiC"] = True
                    elif heat["Heat"] == "SA1":
                        if klasse["SemiC"] is False:
                            _newvalue = {"TidSemi": heat["Start"]}
                            result = await db.klasser_collection.update_one(
                                _myquery, {"$set": _newvalue}
                            )
                            logging.debug(result)
                    elif heat["Heat"] == "FC":
                        _newvalue = {"TidFinale": heat["Start"]}
                        result = await db.klasser_collection.update_one(
                            _myquery, {"$set": _newvalue}
                        )
                        klasse["FinaleC"] = True
                        logging.debug(result)
                    elif heat["Heat"] == "FB":
                        klasse["FinaleB"] = True
                        if klasse["FinaleC"] is False:
                            _newvalue = {"TidFinale": heat["Start"]}
                            result = await db.klasser_collection.update_one(
                                _myquery, {"$set": _newvalue}
                            )
                            logging.debug(result)
                    elif heat["Heat"] == "FA":
                        if (klasse["FinaleC"] or klasse["FinaleB"]) is False:
                            _newvalue = {"TidFinale": heat["Start"]}
                            result = await db.klasser_collection.update_one(
                                _myquery, {"$set": _newvalue}
                            )
                            logging.debug(result)
                    elif heat["Heat"] == "F1":
                        _newvalue = {"TidKvart": heat["Start"]}
                        result = await db.klasser_collection.update_one(
                            _myquery, {"$set": _newvalue}
                        )
                        logging.debug(result)
                    elif heat["Heat"] == "A1":
                        _newvalue = {"TidSemi": heat["Start"]}
                        result = await db.klasser_collection.update_one(
                            _myquery, {"$set": _newvalue}
                        )
                        logging.debug(result)

        return returncode
