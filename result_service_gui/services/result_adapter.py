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

    async def get_race_results(self, token: str, race_id: str) -> List:
        """Get all results for one race."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        results = []
        async with ClientSession() as session:
            async with session.get(
                f"{RACE_SERVICE_URL}/races/{race_id}/race-results", headers=headers
            ) as resp:
                logging.debug(f"get_race_results - got response {resp.status}")
                if resp.status == 200:
                    results = await resp.json()
                else:
                    servicename = "get_race_results"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return results
