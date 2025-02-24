"""Module for status adapter."""

import copy
import logging
import os

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

from .config_adapter import ConfigAdapter
from .events_adapter import EventsAdapter

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class StatusAdapter:
    """Class representing status."""

    async def get_status(self, token: str, event: dict, count: int) -> list:
        """Get latest status messages."""
        status = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_status"

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/status?count={count}&eventId={event['id']}",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    status = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise Exception(f"Error - {resp.status}: {body['detail']}.")
        return status

    async def get_status_by_type(
        self, token: str, event: dict, type: str, count: int
    ) -> list:
        """Get latest status messages for a given type."""
        status = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_status"
        status_type = await ConfigAdapter().get_config(token, event, type)

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/status?count={count}&eventId={event['id']}&type={status_type}",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    status = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise Exception(f"Error - {resp.status}: {body['detail']}.")
        return status

    async def create_status(
        self, token: str, event: dict, type: str, message: str
    ) -> str:
        """Create new status function."""
        servicename = "create_status"
        time = EventsAdapter().get_local_time(event, "log")
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        status_dict = {
            "event_id": event["id"],
            "time": time,
            "type": type,
            "message": message,
        }
        request_body = copy.deepcopy(status_dict)

        async with ClientSession() as session:
            async with session.post(
                f"{PHOTO_SERVICE_URL}/status", headers=headers, json=request_body
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

    async def delete_all_status(self, token: str, event: dict) -> int:
        """Delete all status function."""
        servicename = "delete_status"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{PHOTO_SERVICE_URL}/status?event_id={event['id']}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                pass
            logging.debug(f"Delete status: {id} - res {resp.status}")
            if resp.status == 204:
                logging.debug(f"result - got response {resp}")
            else:
                logging.error(f"{servicename} failed - {resp.status} - {resp}")
                raise web.HTTPBadRequest(reason=f"Error - {resp.status}: {resp}.")
        return resp.status
