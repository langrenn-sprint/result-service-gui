"""Module for photo timing service."""

import logging

from .events_adapter import EventsAdapter
from .photos_adapter import PhotosAdapter
from .raceplans_adapter import RaceplansAdapter
from .time_events_service import TimeEventsService


class PhotoTimingService:
    """Class representing service layer for photo_timing."""

    async def create_time_events_from_photos(self, user: dict, race_id: str) -> str:
        """Identify race_id for a time_event."""
        informasjon = ""
        try:
            race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)
            event = await EventsAdapter().get_event(user["token"], race["event_id"])
            time_stamp_now = EventsAdapter().get_local_time(event, "log")
            photos = await PhotosAdapter().get_photos_by_race_id(user["token"], race_id)
            for photo in photos:
                bibs = photo["ai_information"]["ai_crop_numbers"]
                if len(bibs) == 1:
                    bib = bibs[0]
                    crossing_time = photo["creation_time"]

                    # determine rank and adjustments in list
                    delete_result_list = []
                    add_result_list = []
                    rank = 1
                    results = race["results"]
                    if len(results) > 0:
                        if "Finish" in results.keys():
                            finish_ranks = results["Finish"]["ranking_sequence"]

                            # check if racer already is in result list
                            for rank_event in finish_ranks:
                                if rank_event["bib"] == bib:
                                    informasjon = (
                                        f"Result already registered for bib {bib}."
                                    )
                                    return informasjon

                            # determine position and insert new result in result list
                            for rank_event in finish_ranks:
                                if rank_event["registration_time"] < crossing_time:
                                    rank += 1
                                else:
                                    rank_event["rank"] += 1
                                    rank_event["id"] = ""
                                    rank_event["changelog"].append(
                                        {
                                            "timestamp": time_stamp_now,
                                            "user_id": user["name"],
                                            "comment": f"Endret resultat basert på foto id {photo['id']}",
                                        }
                                    )
                                    add_result_list.append(rank_event)
                                    delete_result_list.append(rank_event["id"])
                    new_result = {
                        "id": "",
                        "event_id": photo["event_id"],
                        "bib": bib,
                        "rank": rank,
                        "registration_time": crossing_time,
                        "photo['id']": photo["id"],
                        "race": f"{race['raceclass']}-{race['round']}{race['index']}{race['heat']}",
                        "race_id": race["id"],
                        "timing_point": "Finish",
                        "next_race": "",
                        "next_race_id": "",
                        "next_race_position": 0,
                        "status": "OK",
                        "changelog": [
                            {
                                "timestamp": time_stamp_now,
                                "user_id": user["name"],
                                "comment": "Resultat fra foto passering",
                            }
                        ],
                    }
                    add_result_list.append(new_result)
                    informasjon = await TimeEventsService().update_finish_time_events(
                        user, delete_result_list, add_result_list
                    )
        except Exception as e:
            informasjon = f"create_time_event_from_photo: Kunne ikke opprette passering automatisk - {e}"
            logging.error(informasjon)
        return informasjon
