"""Module for raceplans adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

RACE_HOST_SERVER = os.getenv("RACE_HOST_SERVER", "localhost")
RACE_HOST_PORT = os.getenv("RACE_HOST_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_HOST_SERVER}:{RACE_HOST_PORT}"


class StartAdapter:
    """Class representing start."""

    # todo: update
    async def get_startliste_by_lopsklasse(
        self, token: str, event_id: str, raceclass: str
    ) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans", headers=headers
            ) as resp:
                logging.debug(
                    f"get_all_raceplans - got response {resp.status}, raceclass: {raceclass}"
                )
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_startliste_by_lopsklasse"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplans

    # todo: update
    async def get_startliste_by_nr(
        self, token: str, event_id: str, start_bib: str
    ) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans", headers=headers
            ) as resp:
                logging.debug(
                    f"get_all_raceplans - got response {resp.status}, bib {start_bib}"
                )
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_startliste_by_nr"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return raceplans

    async def get_all_starts(self, token: str, event_id: str) -> List:
        """Get all raceplans function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        starts = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans", headers=headers
            ) as resp:
                logging.debug(f"get_all_raceplans - got response {resp.status}")
                if resp.status == 200:
                    starts = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_starts"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            starts = [
                {
                    "bib": "414",  # start number
                    "name": "Taiyo Fuseya Skjærven",  # full name
                    "club": "Rustad IL",
                    "race": "G11KA1",  # race id
                    "pos": "1",  # start line/position
                    "starttime": "10:01:30",
                },
                {
                    "race": "G11KA1",
                    "pos": "2",
                    "bib": "415",
                    "name": "Aksel Lied-Storstenvik",
                    "club": "Kjelsås IL",
                    "starttime": "10:01:30",
                },
                {
                    "race": "G11KA1",
                    "pos": "3",
                    "bib": "416",
                    "name": "Andreas Heggelund Dahl",
                    "club": "Bækkelagets SK",
                    "starttime": "10:01:30",
                },
                {
                    "race": "G11KA1",
                    "pos": "4",
                    "bib": "417",
                    "name": "Theodor Owe",
                    "club": "Kjelsås IL",
                    "starttime": "10:01:30",
                },
                {
                    "race": "G11KA1",
                    "pos": "5",
                    "bib": "418",
                    "name": "Erik Skjellevik Innselset",
                    "club": "Kjelsås IL",
                    "starttime": "10:01:30",
                },
                {
                    "race": "G11KA1",
                    "pos": "6",
                    "bib": "419",
                    "name": "Aleksander Tronsmo-Oraug",
                    "club": "Kjelsås IL",
                    "starttime": "10:01:30",
                },
            ]
        return starts
