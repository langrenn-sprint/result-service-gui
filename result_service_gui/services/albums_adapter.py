"""Module for albums adapter."""

import logging
import os
from typing import List, Optional

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

from result_service_gui.model import Album, AlbumSchema

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class AlbumsAdapter:
    """Class representing albums."""

    async def get_all_albums(self, token: str, event_id: Optional[str]) -> List[Album]:
        """Get all albums function."""
        albums = []
        logging.debug(f"Need to handle event_id {event_id}")
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/albums", headers=headers
            ) as resp:
                logging.debug(f"get_all_albums - got response {resp.status}")
                if resp.status == 200:
                    albums = await resp.json()
                    logging.debug(f"albums - got response {albums}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    logging.error(f"Error {resp.status} getting albums: {resp} ")
        # convert to Album type
        ds_albums = []
        schema = AlbumSchema(many=True)
        ds_albums = schema.load(albums)
        return ds_albums

    async def get_album(self, token: str, id: str) -> Album:
        """Get album function."""
        album = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/albums/{id}", headers=headers
            ) as resp:
                logging.debug(f"get_album {id} - got response {resp.status}")
                if resp.status == 200:
                    album = await resp.json()
                    logging.debug(f"album - got response {album}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_album"
                    body = await resp.json()
                    logging.debug(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        ds_album = AlbumSchema().load(album)
        return ds_album

    async def get_album_by_g_id(self, token: str, g_id: str) -> Optional[Album]:
        """Get album by google id function."""
        album = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_album_by_g_id"

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/albums?gId={g_id}", headers=headers
            ) as resp:
                logging.debug(f"get_album_by_g_id {g_id} - got response {resp.status}")
                if resp.status == 200:
                    album = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                elif resp.status == 500:
                    # no album found
                    return None
                else:
                    body = await resp.json()
                    logging.debug(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        ds_album = AlbumSchema().load(album)
        return ds_album

    async def create_album(self, token: str, album: Album) -> str:
        """Create new album function."""
        servicename = "create_album"
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = AlbumSchema().dump(album)

        async with ClientSession() as session:
            async with session.post(
                f"{PHOTO_SERVICE_URL}/albums", headers=headers, json=request_body
            ) as resp:
                if resp.status == 201:
                    logging.debug(f"result - got response {resp}")
                    location = resp.headers[hdrs.LOCATION]
                    id = location.split(os.path.sep)[-1]
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )

        return id

    async def delete_album(self, token: str, id: str) -> int:
        """Delete album function."""
        servicename = "delete_album"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/albums/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.debug(f"Delete album: {id} - res {resp.status}")
            if resp.status == 204:
                logging.debug(f"result - got response {resp}")
            else:
                logging.error(f"{servicename} failed - {resp.status} - {resp}")
                raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {resp}.")
        return resp.status

    async def update_album(self, token: str, id: str, album: Album) -> str:
        """Update album function."""
        servicename = "update_album"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = AlbumSchema().dump(album)

        async with ClientSession() as session:
            async with session.put(
                f"{PHOTO_SERVICE_URL}/albums/{id}", headers=headers, json=request_body
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update album - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            logging.debug(f"Updated album: {id} - res {resp.status}")
        return str(resp.status)
