"""Module for results adapter."""
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


class ResultAdapter:
    """Class representing result."""

    async def get_all_results(self, token: str, event_id: str) -> List:
        """Get all results - lap time or heat place function."""
        headers = MultiDict(
            {
                hdrs.AUTHORIZATION: f"Bearer {token}",
            }
        )
        results = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/results", headers=headers
            ) as resp:
                logging.debug(f"get_all_results - got response {resp.status}")
                if resp.status == 200:
                    results = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_all_results"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            results = [
                {
                    "bib": "414",  # start number
                    "name": "Taiyo Fuseya Skjærven",  # full name
                    "club": "Rustad IL",
                    "race": "G11KA1",  # race id
                    "point": "Mål",  # point in race where result where registered
                    "rank": "1",  # optional for interval start
                    "time": "10:01:30",  # optional for sprint competition
                    "next_race": "SA1-1",  # optional, only for sprint competition
                },
                {
                    "race": "G11KA1",
                    "bib": "415",
                    "name": "Aksel Lied-Storstenvik",
                    "club": "Kjelsås IL",
                    "rank": "2",
                    "time": "10:01:30",
                    "next_race": "SA1-3",
                },
                {
                    "race": "G11KA1",
                    "bib": "416",
                    "name": "Andreas Heggelund Dahl",
                    "club": "Bækkelagets SK",
                    "rank": "3",
                    "time": "10:01:30",
                    "next_race": "SA1-5",
                },
                {
                    "race": "G11KA1",
                    "bib": "417",
                    "name": "Theodor Owe",
                    "club": "Kjelsås IL",
                    "rank": "4",
                    "time": "10:01:30",
                    "next_race": "SA1-7",
                },
                {
                    "race": "G11KA1",
                    "bib": "418",
                    "name": "Erik Skjellevik Innselset",
                    "club": "Kjelsås IL",
                    "rank": "5",
                    "time": "10:01:30",
                    "next_race": "SC1-1",
                },
                {
                    "race": "G11KA1",
                    "bib": "419",
                    "name": "Aleksander Tronsmo-Oraug",
                    "club": "Kjelsås IL",
                    "rank": "6",
                    "time": "10:01:30",
                    "next_race": "SC1-3",
                },
            ]
        return results
