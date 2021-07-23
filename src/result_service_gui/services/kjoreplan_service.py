"""Module for kjoreplan service."""
import datetime
import logging
from typing import Any, List


class KjoreplanService:
    """Class representing kjoreplan service."""

    async def get_all_heat(self, db: Any) -> List:
        """Get all heat / kjøreplan function."""
        kjoreplan = []
        cursor = db.kjoreplan_collection.find()
        for document in await cursor.to_list(length=500):
            kjoreplan.append(document)
            logging.debug(document)
        return kjoreplan

    async def get_upcoming_heat(self, db: Any, count: int) -> List:
        """Get the next upcoming heat (count)."""
        kjoreplan = []
        i = 0

        timenow = datetime.datetime.now().strftime("%X")
        logging.debug(timenow)

        cursor = db.kjoreplan_collection.find()
        for document in await cursor.to_list(length=500):
            if (document["Start"] > timenow) and (i < count):
                i = i + 1
                kjoreplan.append(document)
                logging.debug(document)
        return kjoreplan

    async def get_heat_by_klasse(self, db: Any, lopsklasse: str) -> List:
        """Get all heat / kjøreplan for a given klasse."""
        kjoreplan = []
        cursor = db.kjoreplan_collection.find({"Løpsklasse": lopsklasse})
        for document in await cursor.to_list(length=500):
            kjoreplan.append(document)
            logging.debug(document)
        return kjoreplan

    async def get_heat_for_live_scroll(self, db: Any, lopsklasse: str) -> List:
        """Get heat / kjøreplan for live scroll."""
        # This method will reduce number of heat to dislpay in live view
        # SemiC does not exist -> show all heat
        # Elif semifinal result registered -> show semi and finals
        # Else -> show quarter and semi finals
        semi_c = False
        semi_result = False
        semi_not_started = True
        kjoreplan = []
        tmp_kjoreplan = []
        cursor = db.kjoreplan_collection.find({"Løpsklasse": lopsklasse})
        # loop throgh heat and determine size and status
        for document in await cursor.to_list(length=500):
            tmp_kjoreplan.append(document)
            logging.debug("Heat: " + document["Heat"])
            if document["Heat"][:2] == "SC":
                semi_c = True
                logging.debug("Found SemiC")
            if (document["Heat"][0] == "S") and (document["resultat_registrert"]):
                semi_result = True
                semi_not_started = False
                logging.debug("Found Semi result")

        # filter out non relevant heat for live view
        for heat in tmp_kjoreplan:
            if semi_c and semi_result and heat["Heat"][0] == "K":
                logging.debug("Ignored kvart - " + heat["Heat"])
            elif semi_c and semi_not_started and heat["Heat"][0] == "F":
                logging.debug("Ignored finale - " + heat["Heat"])
            else:
                kjoreplan.append(heat)
                logging.debug(heat["Heat"])

        return kjoreplan

    async def create_kjoreplan(self, db: Any, body: Any) -> int:
        """Create kjoreplan function. After deletion of existing instances, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)

        # format time
        for heat in body:
            # Format time from decimal to readable format hh:mm:ss:
            time = heat["Start"].replace(",", ".")
            heat["Start"] = _format_time(time)

        # if kjøreplan is updated, only change the heats without resultat_registrert
        if "kjoreplan_collection" in collist:
            returncode = 202
            for heat in body:
                result = await db.kjoreplan_collection.find_one(
                    {"Index": heat["Index"]}
                )
                logging.debug(heat["Index"])

                if result and "resultat_registrert" in result:
                    # resultat registrert - heat kan ikke endres
                    logging.debug("Ignorert: " + result["Index"])
                else:
                    result = await db.kjoreplan_collection.update_one(
                        {"Index": heat["Index"]}, {"$set": heat}
                    )
                    logging.debug(result)
        else:
            result = await db.kjoreplan_collection.insert_many(body)
            logging.debug("inserted %d docs" % (len(result.inserted_ids),))
            _newvalue = {"resultat_registrert": False}
            result = await db.kjoreplan_collection.update_many({}, {"$set": _newvalue})
            logging.debug(result)

        # update tidplan if kjøreplan exists
        if "klasser_collection" in collist:
            await KjoreplanService().update_tidplan(db)
            logging.debug("Updating tidplan")

        return returncode

    async def update_registrer_resultat(self, db: Any, heat: str) -> None:
        """Create kjoreplan function."""
        _myquery = {"Index": heat}
        _newvalue = {"resultat_registrert": True}
        result = await db.kjoreplan_collection.update_one(_myquery, {"$set": _newvalue})
        logging.debug(result)

    async def get_heat_by_index(self, db: Any, index: str) -> dict:
        """Get one klass by lopsklasse function."""
        heat = await db.kjoreplan_collection.find_one({"Index": index})
        logging.debug(heat)
        return heat

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


def _format_time(decimal_time: str) -> str:
    """Format time from decimal to readable format hh:mm:ss."""
    sekunder = int(round(float(decimal_time) * 24 * 60 * 60, 0))
    min = divmod(sekunder, 60)
    hour = divmod(min[0], 60)
    if hour[0] < 10:
        ut_hour = "0" + str(hour[0])
    else:
        ut_hour = str(hour[0])
    if hour[1] < 10:
        ut_min = "0" + str(hour[1])
    else:
        ut_min = str(hour[1])
    if min[1] < 10:
        ut_sek = "0" + str(min[1])
    else:
        ut_sek = str(min[1])
    logging.debug("Tid: " + ut_hour + ":" + ut_min + ":" + ut_sek)

    return ut_hour + ":" + ut_min + ":" + ut_sek
