"""Module for photos adapter."""
import copy
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class PhotosAdapter:
    """Class representing photos."""

    async def get_all_photos(self, token: str) -> List:
        """Get all photos function."""
        photos = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/photos", headers=headers
            ) as resp:
                logging.debug(f"get_all_photos - got response {resp.status}")
                if resp.status == 200:
                    photos = await resp.json()
                    logging.debug(f"photos - got response {photos}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    logging.error(f"Error {resp.status} getting photos: {resp} ")
        return photos

    async def get_photo(self, token: str, id: str) -> dict:
        """Get photo function."""
        photo = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/photos/{id}", headers=headers
            ) as resp:
                logging.debug(f"get_photo {id} - got response {resp.status}")
                if resp.status == 200:
                    photo = await resp.json()
                    logging.debug(f"photo - got response {photo}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_photo"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return photo

    async def get_photo_by_g_id(self, token: str, g_id: str) -> dict:
        """Get photo by google id function."""
        photo = {}
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/photos?gId={g_id}", headers=headers
            ) as resp:
                logging.debug(f"get_photo_by_g_id {g_id} - got response {resp.status}")
                if resp.status == 200:
                    photo = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_photo_by_g_id"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return photo

    async def create_photo(self, token: str, photo: dict) -> str:
        """Create new photo function."""
        servicename = "create_photo"
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = copy.deepcopy(photo)

        async with ClientSession() as session:
            async with session.post(
                f"{PHOTO_SERVICE_URL}/photos", headers=headers, json=request_body
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

    async def delete_photo(self, token: str, id: str) -> str:
        """Delete photo function."""
        servicename = "delete_photo"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/photos/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.debug(f"Delete photo: {id} - res {resp.status}")
            if resp.status == 204:
                logging.debug(f"result - got response {resp}")
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return str(resp.status)

    async def update_photo(self, token: str, id: str, request_body: dict) -> str:
        """Update photo function."""
        servicename = "update_photo"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.put(
                f"{PHOTO_SERVICE_URL}/photos/{id}", headers=headers, json=request_body
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update photo - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            logging.debug(f"Updated photo: {id} - res {resp.status}")
        return str(resp.status)
