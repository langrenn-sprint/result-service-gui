"""Module for albums adapter."""

import logging
import os
from http import HTTPStatus

from aiohttp import ClientSession, hdrs
from multidict import MultiDict

from result_service_gui.model import Album, AlbumSchema

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class AlbumsAdapter:
    """Class representing albums."""

    async def get_all_albums(self, token: str, event_id: str | None) -> list[Album]:
        """Get all albums function."""
        albums = []
        logging.info(f"Need to handle event_id {event_id}")
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/albums", headers=headers,
        ) as resp:
            logging.info(f"get_all_albums - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                albums = await resp.json()
                logging.info(f"albums - got response {albums}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unauthorized - {resp}"
                raise Exception(err_msg)
            else:
                err_msg = f"Error {resp.status} getting albums: {resp} "
                logging.error(err_msg)
        # convert to Album type
        schema = AlbumSchema(many=True)
        return schema.load(albums)  # type: ignore[no-untyped-call]

    async def get_album(self, token: str, album_id: str) -> Album:
        """Get album function."""
        album = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/albums/{album_id}", headers=headers,
        ) as resp:
            logging.info(f"get_album {album_id} - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                album = await resp.json()
                logging.info(f"album - got response {album}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unauthorized - {resp}"
                raise Exception(err_msg)
            else:
                servicename = "get_album"
                body = await resp.json()
                err_msg = f"{servicename} failed - {resp.status} - {body}"
                raise Exception(err_msg)
        return AlbumSchema().load(album)  # type: ignore[no-untyped-call]

    async def get_album_by_g_id(self, token: str, g_id: str) -> Album | None:
        """Get album by google id function."""
        album = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        servicename = "get_album_by_g_id"

        async with ClientSession() as session, session.get(
            f"{PHOTO_SERVICE_URL}/albums?gId={g_id}", headers=headers,
        ) as resp:
            logging.info(f"get_album_by_g_id {g_id} - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                album = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unauthorized - {resp}"
                raise Exception(err_msg)
            elif resp.status == HTTPStatus.INTERNAL_SERVER_ERROR:
                # no album found
                return None
            else:
                body = await resp.json()
                err_msg = f"{servicename} failed - {resp.status} - {body}"
                raise Exception(err_msg)
        return AlbumSchema().load(album)  # type: ignore[no-untyped-call]

    async def create_album(self, token: str, album: Album) -> str:
        """Create new album function."""
        servicename = "create_album"
        result = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        request_body = AlbumSchema().dump(album)

        async with ClientSession() as session, session.post(
            f"{PHOTO_SERVICE_URL}/albums", headers=headers, json=request_body,
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.info(f"result - got response {resp}")
                location = resp.headers[hdrs.LOCATION]
                result = location.split(os.path.sep)[-1]
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unauthorized - {resp}"
                raise Exception(err_msg)
            else:
                body = await resp.json()
                err_msg = f"{servicename} failed - {resp.status} - {body}"
                raise Exception(err_msg)
        return result

    async def delete_album(self, token: str, album_id: str) -> int:
        """Delete album function."""
        servicename = "delete_album"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        url = f"{PHOTO_SERVICE_URL}/albums/{album_id}"
        async with ClientSession() as session, session.delete(
            url, headers=headers,
        ) as resp:
            pass
        logging.info(f"Delete album: {album_id} - res {resp.status}")
        if resp.status == HTTPStatus.NO_CONTENT:
            logging.info(f"result - got response {resp}")
        elif resp.status == HTTPStatus.UNAUTHORIZED:
            err_msg = f"401 Unauthorized - {resp}"
            raise Exception(err_msg)
        else:
            body = await resp.json()
            err_msg = f"{servicename} failed - {resp.status} - {body}"
            raise Exception(err_msg)
        return resp.status

    async def update_album(self, token: str, album_id: str, album: Album) -> str:
        """Update album function."""
        servicename = "update_album"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ],
        )
        request_body = AlbumSchema().dump(album)

        async with ClientSession() as session, session.put(
            f"{
                PHOTO_SERVICE_URL
            }/albums/{album_id}", headers=headers, json=request_body,
        ) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                logging.info(f"update album - got response {resp}")
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unauthorized - {resp}"
                raise Exception(err_msg)
            else:
                body = await resp.json()
                err_msg = f"{servicename} failed - {resp.status} - {body}"
                raise Exception(err_msg)
            logging.info(f"Updated album: {album_id} - res {resp.status}")
        return str(resp.status)
