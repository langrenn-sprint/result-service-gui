"""Module for google photos adapter."""
import logging
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

GOOGLE_PHOTO_SERVER = "https://photoslibrary.googleapis.com/v1"
GOOGLE_PHOTO_CREDENTIALS_FILE = "/home/heming/github/photo_api_credentials.json"


class GooglePhotosAdapter:
    """Class representing google photos."""

    async def get_albums(self) -> List:
        """Get all albums."""
        albums = []
        servicename = "get_albums"
        try:
            f = open(GOOGLE_PHOTO_CREDENTIALS_FILE)
            token = f.read()
            f.close()
        except Exception as e:
            logging.error(f"{servicename} failed - {e}")
            raise web.HTTPBadRequest(reason=f"Error in {servicename}: {e}.") from e

        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        async with ClientSession() as session:
            async with session.get(
                f"{GOOGLE_PHOTO_SERVER}/albums", headers=headers
            ) as resp:
                logging.debug(f"{servicename} - got response {resp.status}")
                if resp.status == 200:
                    albums = await resp.json()
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return albums
