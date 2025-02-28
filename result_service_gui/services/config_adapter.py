"""Module for config adapter."""

import copy
import json
import logging
import os

from aiohttp import ClientSession
from aiohttp import hdrs
from aiohttp import web
from multidict import MultiDict

PHOTOS_HOST_SERVER = os.getenv("PHOTOS_HOST_SERVER", "localhost")
PHOTOS_HOST_PORT = os.getenv("PHOTOS_HOST_PORT", "8092")
PHOTO_SERVICE_URL = f"http://{PHOTOS_HOST_SERVER}:{PHOTOS_HOST_PORT}"


class ConfigAdapter:
    """Class representing config."""

    async def get_config(self, token: str, event: dict, key: str) -> str:
        """Get config by key function."""
        config = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_config"

        async with ClientSession() as session:
            async with session.get(
                f"{PHOTO_SERVICE_URL}/config?key={key}&eventId={event['id']}",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    config = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise Exception(f"Error - {resp.status}: {body['detail']}.")
        return config["value"]  # type: ignore

    async def get_all_configs(self, token: str, event: dict) -> list:
        """Get config by google id function."""
        config = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        servicename = "get_all_configs"
        if event:
            url = f"{PHOTO_SERVICE_URL}/configs?eventId={event['id']}"
        else:
            url = f"{PHOTO_SERVICE_URL}/configs"

        async with ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    config = await resp.json()
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise Exception(f"Error - {resp.status}: {body['detail']}.")
        return config

    async def get_config_bool(self, token: str, event: dict, key: str) -> bool:
        """Get config boolean value."""
        string_value = await self.get_config(token, event, key)
        boolean_value = False
        if string_value in ["True", "true", "1"]:
            boolean_value = True

        return boolean_value

    async def get_config_int(self, token: str, event: dict, key: str) -> int:
        """Get config int value."""
        string_value = await self.get_config(token, event, key)
        return int(string_value)

    async def get_config_list(self, token: str, event: dict, key: str) -> list:
        """Get config list value."""
        string_value = await self.get_config(token, event, key)
        # convert from json string to list
        return json.loads(string_value)

    async def create_config(self, token: str, event: dict, key: str, value: str) -> str:
        """Create new config function."""
        servicename = "create_config"
        id = ""
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        config = {
            "event_id": event["id"],
            "key": key,
            "value": value,
        }
        request_body = copy.deepcopy(config)

        async with ClientSession() as session:
            async with session.post(
                f"{PHOTO_SERVICE_URL}/config", headers=headers, json=request_body
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

    async def init_config(self, token: str, event: dict) -> None:
        """Load default config function - read from file."""
        PROJECT_ROOT = os.path.join(os.getcwd(), "result_service_gui")
        config_file = f"{PROJECT_ROOT}/config/global_settings.json"

        current_configs = await ConfigAdapter().get_all_configs(token, event)

        try:
            with open(config_file, "r") as json_file:
                settings = json.load(json_file)
                for key, value in settings.items():
                    updated = False
                    for config in current_configs:
                        if config["key"] == key:
                            await self.update_config(token, event, key, value)
                            updated = True
                            break
                    if not updated:
                        await self.create_config(token, event, key, value)
        except Exception as e:
            err_info = f"Error linitializing config from {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from e

    async def update_config_list(
        self, token: str, event: dict, key: str, new_value: list
    ) -> str:
        """Update config list value."""
        new_value_str = json.dumps(new_value)
        result = await self.update_config(token, event, key, new_value_str)
        return result

    async def update_config(
        self, token: str, event: dict, key: str, new_value: str
    ) -> str:
        """Update config function."""
        servicename = "update_config"
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = {
            "event_id": event["id"],
            "key": key,
            "value": new_value,
        }

        async with ClientSession() as session:
            async with session.put(
                f"{PHOTO_SERVICE_URL}/config", headers=headers, json=request_body
            ) as resp:
                if resp.status == 204:
                    logging.debug(f"update config - got response {resp}")
                elif resp.status == 401:
                    raise web.HTTPBadRequest(reason=f"401 Unathorized - {servicename}")
                else:
                    body = await resp.json()
                    logging.error(f"{servicename} failed - {resp.status} - {body}")
                    raise web.HTTPBadRequest(
                        reason=f"Error - {resp.status}: {body['detail']}."
                    )
            logging.debug(f"Updated config: {id} - res {resp.status}")
        return str(resp.status)
