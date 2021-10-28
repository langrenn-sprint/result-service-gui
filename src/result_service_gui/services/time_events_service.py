"""Module for time event service."""
import logging

from result_service_gui.services import (
    RaceplansAdapter,
    TimeEventsAdapter,
)


class TimeEventsService:
    """Class representing service layer for time_events."""

    async def create_time_event(self, token: str, time_event: dict) -> str:
        """Validate, enrich and create new start and time_event."""
        logging.info(f"Got time-event: {time_event}")
        # 1. First enrich data
        # check if race_id exists
        if time_event["race_id"] == "":
            time_event["race_id"] = await find_race_id_from_time_event(
                token, time_event
            )

        # 2. Check for duplicate time events
        # TODO

        # 3. Create or update time event
        id = await TimeEventsAdapter().create_time_event(token, time_event)

        # 4. Calculate next race and position
        next_start_entry = await get_next_start_entry(token, time_event)
        logging.info(next_start_entry)
        # 5. Create new start event

        return id

    async def update_time_event(self, token: str, id: str, time_event: dict) -> str:
        """Validate, enrich and update start and time_event."""
        informasjon = await TimeEventsAdapter().update_time_event(token, id, time_event)
        return informasjon


async def get_next_start_entry(token: str, time_event: dict) -> dict:
    """Generate start_entry - based upon a time_event."""
    start_entry = {
        "race_id": "",
        "bib": 1,
        "starting_position": 1,
        "scheduled_start_time": "",
    }

    next_race_rule = []
    next_race = [
        {
            "round": "SA",
            "contestants_qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "SC",
            "contestants_qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FA",
            "contestants_qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB",
            "contestants_qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC",
            "contestants_qualified": 0,
            "current_contestant_qualified": False,
        },
    ]

    # find relevant race and get next race rule
    raceplans = await RaceplansAdapter().get_all_raceplans(
        token, time_event["event_id"]
    )
    if len(raceplans) > 0:
        races = raceplans[0]["races"]
        for race in races:
            if race["id"] == time_event["race_id"]:
                next_race_rule = race["rule"]

    # interpret rule part 1 - number of racers qualified to next round
    for key, value in next_race_rule.items():
        if key == "S":
            for x, y in value.items():
                if x == "A" and y > 0:
                    next_race[0]["contestants_qualified"] = y
                elif x == "C" and y > 0:
                    next_race[1]["contestants_qualified"] = y
        elif key == "F":
            for x, y in value.items():
                if x == "A":
                    next_race[2]["contestants_qualified"] = y
                elif x == "B" and y > 8:
                    next_race[3]["contestants_qualified"] = y
                elif x == "C":
                    next_race[4]["contestants_qualified"] = y

    # interpret rule part 2 - find next round and get race id
    i_aggregate_qualification_place = 0
    for race_item in next_race:
        if (
            int(time_event["rank"])
            <= race_item["contestants_qualified"] + i_aggregate_qualification_place
        ):
            race_item["current_contestant_qualified"] = True
            # now we have next round - get race id
            # start_entry["race_id"] = find_race_id_from_round_and_time_event(
            #    token, race_item["round"], time_event["event_id"], races
            # )
            break
        else:
            i_aggregate_qualification_place += race_item["contestants_qualified"]

    logging.info(f"Race item: {next_race}")
    return start_entry


def find_race_id_from_round_and_time_event(
    token: str, round: str, time_event: dict, races: list
) -> str:
    """Identify next race_id given round."""
    # 1. Get previous race and all possible next race candidates
    next_race_candidates = []
    for race in races:
        if race["id"] == time_event["race_id"]:
            previous_race = race
        elif race["round"] == round:
            next_race_candidates.append[race]

    # 2. Select the right next_race based upon last heat and rank
    race_id = previous_race["id"]

    # validate registration time_for confirmation
    return race_id


async def find_race_id_from_time_event(token: str, time_event: dict) -> str:
    """Identify race_id for a time_event."""
    race_id = "Todo"
    # get start(s) for contestants

    # validate registration time_for confirmation
    return race_id
