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
        """Get all results function."""
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
        return results
