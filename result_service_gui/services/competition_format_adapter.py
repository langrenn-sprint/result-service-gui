"""Module for events adapter."""
import logging
import os
from typing import List

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

COMPETITION_FORMAT_HOST_SERVER = os.getenv("COMPETITION_FORMAT_HOST_SERVER", "localhost")
COMPETITION_FORMAT_HOST_PORT = os.getenv("COMPETITION_FORMAT_HOST_PORT", "8094")
COMPETITION_FORMAT_SERVICE_URL = (
    f"http://{COMPETITION_FORMAT_HOST_SERVER}:{COMPETITION_FORMAT_HOST_PORT}"
)


class CompetitionFormatAdapter:
    """Class representing events."""

    async def create_competition_format(self, token: str, request_body: dict) -> str:
        """Generate create_competition_format standard values."""
        servicename = "create_competition_format"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats"
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=request_body) as resp:
                res = resp.status
                logging.debug(f"create_competition_format result - got response {resp}")
                if res == 201:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Opprettet competition format {resp.status}."
        return information

    async def delete_competition_format(self, token: str, id: str) -> str:
        """Function to delete one competition_format."""
        servicename = "delete_competition_format"
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                res = resp.status
                logging.debug(f"delete_competition_format result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Slettet competition format {resp.status}."
        return information

    async def get_competition_formats(self, token: str) -> List:
        """Get competition_formats function."""
        competition_formats = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats", headers=headers
            ) as resp:
                logging.debug(f"get_competition_formats - got response {resp.status}")
                if resp.status == 200:
                    competition_formats = await resp.json()
                    logging.debug(
                        f"competition_formats - got response {competition_formats}"
                    )
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_competition_formats"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return competition_formats

    async def update_competition_format(self, token: str, request_body: dict) -> str:
        """Generate update_competition_format standard values."""
        servicename = "update_competition_format"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/competition-formats/{request_body['id']}"
        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=request_body) as resp:
                res = resp.status
                logging.debug(f"update_competition_format result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Oppdatert competition format {resp.status}."
        return information

    async def create_race_config(self, token: str, request_body: dict) -> str:
        """Generate create_race_config standard values."""
        servicename = "create_race_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs"
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=request_body) as resp:
                res = resp.status
                logging.debug(f"create_race_config result - got response {resp}")
                if res == 201:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Opprettet race-config {resp.status}."
        return information

    async def delete_race_config(self, token: str, id: str) -> str:
        """Function to delete one race_config."""
        servicename = "delete_race_config"
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs/{id}"
        async with ClientSession() as session:
            async with session.delete(url, headers=headers) as resp:
                res = resp.status
                logging.debug(f"delete_race_config result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Slettet race-config {resp.status}."
        return information

    async def get_race_configs(self, token: str) -> List:
        """Get race_configs function."""
        race_configs = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs", headers=headers
            ) as resp:
                logging.debug(f"get_race_configs - got response {resp.status}")
                if resp.status == 200:
                    race_configs = await resp.json()
                    logging.debug(
                        f"race_configs - got response {race_configs}"
                    )
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    servicename = "get_race_configs"
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        return race_configs

    async def update_race_config(self, token: str, request_body: dict) -> str:
        """Generate update_race_config standard values."""
        servicename = "update_race_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        url = f"{COMPETITION_FORMAT_SERVICE_URL}/race-configs/{request_body['id']}"
        async with ClientSession() as session:
            async with session.put(url, headers=headers, json=request_body) as resp:
                res = resp.status
                logging.debug(f"update_race_config result - got response {resp}")
                if res == 204:
                    pass
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
        information = f"Oppdatert race-config {resp.status}."
        return information
