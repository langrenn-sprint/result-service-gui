"""Module for start adapter."""

from http import HTTPStatus
import logging
import os

from aiohttp import ClientSession, hdrs, web
from multidict import MultiDict

RACE_HOST_SERVER = os.getenv("RACE_HOST_SERVER", "localhost")
RACE_HOST_PORT = os.getenv("RACE_HOST_PORT", "8088")
RACE_SERVICE_URL = f"http://{RACE_HOST_SERVER}:{RACE_HOST_PORT}"


class StartAdapter:
    """Class representing start."""

    async def generate_startlist_for_event(self, token: str, event_id: str) -> str:
        """Generate new start_list function."""
        servicename = "generate_startlist_for_event"
        informasjon = ""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        request_body = {"event_id": event_id}
        async with ClientSession() as session, session.post(
            f"{RACE_SERVICE_URL}/startlists/generate-startlist-for-event",
            headers=headers,
            json=request_body,
        ) as resp:
            if resp.status == HTTPStatus.CREATED:
                logging.debug(f"generate_startlist_for_event - got response {resp}")
                location = resp.headers[hdrs.LOCATION]
                s_id = location.split(os.path.sep)[-1]
                informasjon = f"Suksess! Opprettet startlister. Id: {s_id}"
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return informasjon

    async def delete_start_entry(
        self, token: str, race_id: str, start_entry_id: str
    ) -> str:
        """Delete one start_entry function."""
        servicename = "delete_start_entry"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }

        async with ClientSession() as session, session.delete(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_entry_id}",
            headers=headers,
        ) as resp:
            res = resp.status
            logging.debug(f"delete result - got response {resp}")
            if res == HTTPStatus.NO_CONTENT:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return str(res)

    async def delete_start_list(self, token: str, start_list_id: str) -> str:
        """Delete one start_list function."""
        servicename = "delete_start_list"
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        async with ClientSession() as session, session.delete(
            f"{RACE_SERVICE_URL}/startlists/{start_list_id}",
            headers=headers,
        ) as resp:
            res = resp.status
            logging.debug(f"delete result - got response {resp}")
            if res == HTTPStatus.NO_CONTENT:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return str(res)

    async def get_start_entries_by_race_id(self, token: str, race_id: str) -> list:
        """Get one start_entry - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        start_entries = []
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entries_by_race_id - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                start_entries = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                servicename = "get_start_entries_by_race_id"
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return start_entries

    async def get_start_entry_by_id(
        self, token: str, race_id: str, start_id: str
    ) -> dict:
        """Get one start_entry - lap time or heat place function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        start_entry = {}
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/races/{race_id}/start-entries/{start_id}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entry_by_id - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                start_entry = await resp.json()
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"Login expired: {resp}"
                raise Exception(err_msg)

            else:
                servicename = "get_start_entry_by_id"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return start_entry

    async def get_start_entries_by_bib(
        self, token: str, event_id: str, bib: int
    ) -> list:
        """Get all start_entries by bib function."""
        startlists: list[dict] = []
        start_entries: list[dict] = []
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/startlists?eventId={event_id}&bib={bib}",
            headers=headers,
        ) as resp:
            logging.debug(f"get_start_entries_by_bib - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                startlists = await resp.json()
            else:
                servicename = "get_start_entries_by_bib"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )

        if len(startlists) > 0:
            start_entries = startlists[0]["start_entries"]
        return start_entries

    async def get_all_starts_by_event(self, token: str, event_id: str) -> list:
        """Get all starts function."""
        headers = MultiDict(
            [
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )
        starts = []
        async with ClientSession() as session, session.get(
            f"{RACE_SERVICE_URL}/startlists?eventId={event_id}", headers=headers
        ) as resp:
            logging.debug(f"get_all_starts_by_event - got response {resp.status}")
            if resp.status == HTTPStatus.OK:
                starts = await resp.json()
            else:
                servicename = "get_all_starts_by_event"
                body = await resp.json()
                logging.error(f"{servicename} failed - {resp.status} - {body}")
                raise web.HTTPBadRequest(
                    reason=f"Error - {resp.status}: {body['detail']}."
                )
        return starts

    async def create_start_entry(self, token: str, new_start: dict) -> int:
        """Add one start to the start_list."""
        servicename = "create_start_entry"
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session, session.post(
            f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries",
            headers=headers,
            json=new_start,
        ) as resp:
            logging.debug(f"create_start_entry - got response {resp.status}")
            if resp.status == HTTPStatus.CREATED:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return resp.status

    async def update_start_entry(self, token: str, s_id: str, new_start: dict) -> int:
        """Update one start in the start_list."""
        servicename = "update_start_entry"
        headers = {
            hdrs.CONTENT_TYPE: "application/json",
            hdrs.AUTHORIZATION: f"Bearer {token}",
        }
        logging.debug(f"New start: {new_start}")
        async with ClientSession() as session, session.put(
            f"{RACE_SERVICE_URL}/races/{new_start['race_id']}/start-entries/{s_id}",
            headers=headers,
            json=new_start,
        ) as resp:
            logging.debug(f"update_start_entry - got response {resp.status}")
            if resp.status == HTTPStatus.CREATED:
                pass
            elif resp.status == HTTPStatus.UNAUTHORIZED:
                err_msg = f"401 Unathorized - {servicename}"
                raise web.HTTPBadRequest(reason=err_msg)
            else:
                body = await resp.json()
                logging.error(f"{servicename} failed: {resp.status} - {body['detail']}")
                raise web.HTTPBadRequest(
                    reason=f"{servicename} failed - {body['detail']}."
                )
        return resp.status
