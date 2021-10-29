"""Module for time event service."""
import logging

from result_service_gui.services import (
    RaceplansAdapter,
    StartAdapter,
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
        logging.info(f"{next_start_entry}")
        # 5. Create new start event
        id = await StartAdapter().add_one_start(
            token, time_event["event_id"], next_start_entry
        )

        return id

    async def update_time_event(self, token: str, id: str, time_event: dict) -> str:
        """Validate, enrich and update start and time_event."""
        informasjon = await TimeEventsAdapter().update_time_event(token, id, time_event)
        return informasjon


async def get_next_start_entry(token: str, time_event: dict) -> dict:
    """Generate start_entry - based upon a time_event."""
    start_entry = {}
    next_race = next_race_template()

    # find relevant race and get next race rule
    raceplans = await RaceplansAdapter().get_all_raceplans(
        token, time_event["event_id"]
    )
    if len(raceplans) > 0:
        races = raceplans[0]["races"]
        for race in races:
            if race["id"] == time_event["race_id"]:
                for key, value in race["rule"].items():
                    if key == "S":
                        for x, y in value.items():
                            if x == "A" and y > 0:
                                next_race[0]["qualified"] = y
                            elif x == "C" and y > 0:
                                next_race[1]["qualified"] = y
                    elif key == "F":
                        for x, y in value.items():
                            if x == "A":
                                next_race[2]["qualified"] = y
                            elif x == "B" and y > 8:
                                next_race[3]["qualified"] = y
                            elif x == "C":
                                next_race[4]["qualified"] = y

    # interpret rule part 2 - find next round and get race id
    ilimitplace = 0
    ilimitcurrent = 0
    for race_item in next_race:
        ilimitcurrent = race_item["qualified"]
        limit_rank = ilimitcurrent + ilimitplace
        if int(time_event["rank"]) <= limit_rank:
            race_item["current_contestant_qualified"] = True
            # now we have next round - get race id
            start_entry = await generate_new_start_entry(
                token, race_item["round"], time_event, races
            )
            break
        else:
            ilimitplace = limit_rank
    return start_entry


async def generate_new_start_entry(
    token: str, round: str, time_event: dict, races: list
) -> dict:
    """Identify next race_id and generate start entry data."""
    start_entry = {
        "race_id": "",
        "bib": time_event["bib"],
        "starting_position": time_event["rank"],
        "scheduled_start_time": "",
    }
    previous_race = {}
    next_race_candidates = []
    # 1. Get previous race and all possible next race candidates
    for race in races:
        if race.get("id") == time_event.get("race_id"):
            previous_race = race
        elif f"{race.get('round')}{race.get('index')}" == round:
            if previous_race.get("raceclass") == race.get("raceclass"):
                next_race_candidates.append(race)

    # 2. pick a next race - initial rule is to always use first
    if len(next_race_candidates) > 0:
        start_entry["race_id"] = next_race_candidates[0].get("id")
        start_entry["scheduled_start_time"] = next_race_candidates[0].get("start_time")

    return start_entry


async def find_race_id_from_time_event(token: str, time_event: dict) -> str:
    """Identify race_id for a time_event."""
    race_id = "Todo"
    # get start(s) for contestants

    # validate registration time_for confirmation
    return race_id


def next_race_template() -> list:
    """Return template settings for next race."""
    return [
        {
            "round": "SA",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "SC",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FA",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FB",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
        {
            "round": "FC",
            "qualified": 0,
            "current_contestant_qualified": False,
        },
    ]
