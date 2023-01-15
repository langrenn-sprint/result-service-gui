"""Resource module for start resources."""
import json
import logging

from aiohttp import web

from result_service_gui.services import (
    ContestantsAdapter,
    RaceplansAdapter,
    TimeEventsAdapter,
)
from .utils import (
    check_login,
)


class TimingInfo(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the passeringer page."""
        try:
            action = self.request.rel_url.query["action"]
        except Exception:
            action = ""
        event_id = self.request.rel_url.query["event_id"]
        try:
            user = await check_login(self)
            if action == "DNS":
                race_order = int(self.request.rel_url.query["race_order"])
                response = await get_dns(user, event_id, race_order)
            elif action == "search_contestant":
                search_string = str(self.request.rel_url.query["search_string"])
                contestants = await ContestantsAdapter().search_contestants_by_name(user["token"], event_id, search_string)
                response = {"contestants" : contestants}
            json_response = json.dumps(response)
            return web.Response(body=json_response)

        except Exception as e:
            error_message = "Det oppstod en feil ved henting av DNS"
            logging.error(f"Error: {e}. {error_message}")
            return web.Response(body=error_message)


async def get_dns(user: dict, event_id: str, race_order: int) -> dict:
    """Get dns data for one racer."""
    race = await RaceplansAdapter().get_race_by_order(user["token"], event_id, race_order)
    if race:
        dns_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
            user["token"], race["id"]
        )
        dns_list = []
        for entry in dns_time_events:
            if entry['timing_point'] == "DNS":
                dns_list.append(entry["bib"])
        response = {
            "race_order": race_order,
            "dns_list": dns_list
        }
    else:
        response = {"informasjon": "Ukjent action"}
    return response
