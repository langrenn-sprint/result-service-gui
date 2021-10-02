"""Utilities module for gui services."""
import logging

from result_service_gui.services import EventsAdapter


async def get_event(token: str, event_id: str) -> dict:
    """Extract jwt_token from authoricd zation header in request."""
    event = {"name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event
