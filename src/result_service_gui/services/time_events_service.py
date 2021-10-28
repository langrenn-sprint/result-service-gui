"""Module for time event service."""
import logging

from result_service_gui.services import (
    TimeEventsAdapter,
)


class TimeEventsService:
    """Class representing service layer for time_events."""

    async def create_time_event(self, token: str, time_event: dict) -> str:
        """Validate, enrich and create new start and time_event."""
        logging.info(f"Got time-event: {time_event}")
        # check if race_id exists
        if time_event["race_id"] == "":
            time_event["race_id"] = await find_race_id(token, time_event)

        id = await TimeEventsAdapter().create_time_event(token, time_event)

        return id

    async def update_time_event(self, token: str, id: str, time_event: dict) -> str:
        """Validate, enrich and update start and time_event."""
        informasjon = await TimeEventsAdapter().update_time_event(token, id, time_event)
        return informasjon


async def find_race_id(token: str, time_event: dict) -> str:
    """Identify race_id for a time_event."""
    race_id = "Test"
    # get start(s) for contestants

    # validate registration time_for confirmation
    return race_id
