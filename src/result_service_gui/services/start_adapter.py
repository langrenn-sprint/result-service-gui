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
        raceplans = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/raceplans", headers=headers
            ) as resp:
                logging.debug(f"get_all_raceplans - got response {resp.status}")
                if resp.status == 200:
                    raceplans = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_starts"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            raceplans = [
                {
                    "Heat": "G11KA1",
                    "Pos": "1",
                    "Nr": "414",
                    "Navn": "Taiyo Fuseya Skjærven",
                    "Klubb": "Rustad IL",
                    "Plass": "1",
                    "starttime": "10:01:30",
                    "Videre til": "SA1-1",
                },
                {
                    "Heat": "G11KA1",
                    "Pos": "2",
                    "Nr": "415",
                    "Navn": "Aksel Lied-Storstenvik",
                    "Klubb": "Kjelsås IL",
                    "Plass": "2",
                    "starttime": "10:01:30",
                    "Videre til": "SA1-3",
                },
                {
                    "Heat": "G11KA1",
                    "Pos": "3",
                    "Nr": "416",
                    "Navn": "Andreas Heggelund Dahl",
                    "Klubb": "Bækkelagets SK",
                    "Plass": "3",
                    "starttime": "10:01:30",
                    "Videre til": "SA1-5",
                },
                {
                    "Heat": "G11KA1",
                    "Pos": "4",
                    "Nr": "417",
                    "Navn": "Theodor Owe",
                    "Klubb": "Kjelsås IL",
                    "Plass": "4",
                    "starttime": "10:01:30",
                    "Videre til": "SA1-7",
                },
                {
                    "Heat": "G11KA1",
                    "Pos": "5",
                    "Nr": "418",
                    "Navn": "Erik Skjellevik Innselset",
                    "Klubb": "Kjelsås IL",
                    "Plass": "5",
                    "starttime": "10:01:30",
                    "Videre til": "SC1-1",
                },
                {
                    "Heat": "G11KA1",
                    "Pos": "6",
                    "Nr": "419",
                    "Navn": "Aleksander Tronsmo-Oraug",
                    "Klubb": "Kjelsås IL",
                    "Plass": "6",
                    "starttime": "10:01:30",
                    "Videre til": "SC1-3",
                },
            ]
        return raceplans
