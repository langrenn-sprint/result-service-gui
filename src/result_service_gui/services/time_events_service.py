"""Module for time event service."""
import datetime
import logging

from result_service_gui.services import (
    ContestantsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
)


class TimeEventsService:
    """Class representing service layer for time_events."""

    async def generate_next_race_templates(self, token: str, event_id: str) -> str:
        """Calculate next race for the entire team."""
        informasjon = ""
        i = 0
        time_now = datetime.datetime.now()
        time_event = {
            "bib": "",
            "event_id": event_id,
            "race": "",
            "race_id": "",
            "timing_point": "Template",
            "rank": "",
            "registration_time": time_now.strftime("%X"),
            "next_race": "",
            "next_race_id": "",
            "next_race_position": 0,
            "status": "OK",
            "changelog": [],
        }
        # 1. delete all existing Template time events
        current_templates = (
            await TimeEventsAdapter().get_time_events_by_event_id_and_timing_point(
                token, event_id, "Template"
            )
        )
        for template in current_templates:
            id = await TimeEventsAdapter().delete_time_event(token, template["id"])

        # 2. get list of all races and loop, except finals.
        races = await RaceplansAdapter().get_all_races(token, event_id)
        if len(races) == 0:
            informasjon = f"{informasjon} Ingen kjøreplaner funnet."
        else:
            for race in races:
                if race["round"] != "F":
                    time_event[
                        "race"
                    ] = f"{race['raceclass']}-{race['round']}{race['heat']}{race['index']}"
                    time_event["race_id"] = race["id"]

                    # loop and simulate result for pos 1 to 8
                    for x in range(1, 9):
                        time_event["rank"] = x
                        next_start_entry = await get_next_start_entry(token, time_event)
                        logging.debug(f"Time_event: {time_event}")
                        logging.debug(f"Start_entry: {next_start_entry}")
                        if len(next_start_entry) > 0:
                            time_event["next_race"] = next_start_entry["race_round"]
                            time_event["next_race_id"] = next_start_entry["race_id"]
                            time_event["next_race_position"] = next_start_entry[
                                "starting_position"
                            ]
                        else:
                            time_event["next_race"] = "Ute"
                            time_event["next_race_position"] = 0

                        id = await TimeEventsAdapter().create_time_event(
                            token, time_event
                        )
                        logging.debug(f"Created template: {id}")
                        i += 1
        informasjon = f"Suksess! Opprettet {i} templates. "
        return informasjon

    async def create_time_event(self, token: str, time_event: dict) -> str:
        """Validate, enrich and create new start and time_event."""
        # 1. First enrich data
        informasjon = ""
        if time_event["race_id"] == "":
            time_event["race_id"] = await find_race_id_from_time_event(
                token, time_event
            )

        if time_event["timing_point"] == "Start":
            # just register start - nothing more to enrich
            pass
        elif time_event["timing_point"] == "Finish":
            # 3. Get next race from template
            id2 = ""
            next_start_template = {}
            next_start_entries = await TimeEventsAdapter().get_time_events_by_race_id(
                token, time_event["race_id"]
            )
            for entry in next_start_entries:
                if (entry["timing_point"] == "Template") and (
                    entry["rank"] == int(time_event["rank"])
                ):
                    next_start_template = entry

            # 4. Create or update time event
            if len(next_start_template) > 0:
                time_event["next_race"] = next_start_template["next_race"]
                time_event["next_race_id"] = next_start_template["next_race_id"]
                time_event["next_race_position"] = next_start_template[
                    "next_race_position"
                ]

                start_list = await StartAdapter().get_all_starts_by_event(
                    token, time_event["event_id"]
                )
                logging.info(f"Startlist id: {start_list[0]['id']}")
                next_race = await RaceplansAdapter().get_race_by_id(
                    token, time_event["next_race_id"]
                )

                contestants = await ContestantsAdapter().get_contestants_by_bib(
                    token, time_event["event_id"], time_event["bib"]
                )
                if len(contestants) == 1:
                    contestant = contestants[0]
                    # create next start entry
                    next_start_entry = {
                        "race_id": time_event["next_race_id"],
                        "startlist_id": start_list[0]["id"],
                        "bib": time_event["bib"],
                        "name": f"{contestant['first_name']} {contestant['last_name']}",
                        "club": contestant["club"],
                        "scheduled_start_time": next_race["start_time"],
                        "starting_position": time_event["next_race_position"],
                        "status": "OK",
                    }
                    id2 = await StartAdapter().create_start_entry(
                        token, next_start_entry
                    )
                    informasjon += f" Created start event {id2}. "
        id1 = await TimeEventsAdapter().create_time_event(token, time_event)
        informasjon += f" Created time event {id1}. "

        return informasjon

    async def update_time_event(self, token: str, id: str, time_event: dict) -> str:
        """Validate, enrich and update start and time_event."""
        informasjon = await TimeEventsAdapter().update_time_event(token, id, time_event)
        return informasjon


async def get_next_start_entry(token: str, time_event: dict) -> dict:
    """Generate start_entry - empty result if not qualified."""
    start_entry = {}
    next_race = next_race_template()

    # find relevant race and get next race rule
    races = await RaceplansAdapter().get_all_races(token, time_event["event_id"])
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
                        elif x == "B":
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
            time_event["rank_qualified"] = int(time_event["rank"]) - ilimitplace
            start_entry = await calculate_next_start_entry(
                token, race_item, time_event, races
            )
            break
        else:
            ilimitplace = limit_rank
    return start_entry


async def calculate_next_start_entry(
    token: str, race_item: dict, time_event: dict, races: list
) -> dict:
    """Identify next race_id and generate start entry data."""
    start_entry = {
        "bib": time_event["bib"],
        "race_id": "",
        "race_round": "",
        "scheduled_start_time": "",
        "starting_position": time_event["rank_qualified"],
    }
    previous_race = {}
    previous_heat_count = 0
    next_race_candidates = []
    next_race_count = 0
    # 1. Get previous race and all possible next race candidates
    for race in races:
        if race.get("id") == time_event.get("race_id"):
            previous_race = race
            previous_heat_count = race.get("heat")
        elif (
            len(previous_race) > 0
            and previous_race.get("round") == race.get("round")
            and previous_race.get("index") == race.get("index")
            and previous_race.get("raceclass") == race.get("raceclass")
        ):
            previous_heat_count = race.get("heat")
        elif f"{race.get('round')}{race.get('index')}" == race_item["round"]:
            if previous_race.get("raceclass") == race.get("raceclass"):
                next_race_candidates.append(race)

    # 2. pick a next race
    next_race_count = len(next_race_candidates)
    if next_race_count > 0:
        # estimated rank from previous round is:
        # no_of_previous_heat*(rank-1) + rank
        previous_heat_rank = int(time_event["rank_qualified"])
        previous_heat_number = int(previous_race["heat"])
        previous_round_rank = (
            previous_heat_count * (previous_heat_rank - 1) + previous_heat_number
        )

        # distribute contestants evenly in next round, winners in pos 1 osv.
        next_race_tuple = divmod(
            previous_round_rank + (next_race_count - 1), next_race_count
        )
        # quotient gives the position
        next_race_position = next_race_tuple[0]
        # remainder gives the heat, need to add one as heat number starts on 1
        next_race_heat = next_race_tuple[1] + 1

        for race in next_race_candidates:
            if race.get("heat") == next_race_heat:
                logging.debug(f"Found next race: {race}")
                start_entry["race_id"] = race.get("id")
                start_entry["scheduled_start_time"] = race.get("start_time")
                start_entry[
                    "race_round"
                ] = f"{race.get('round')}{race.get('index')}{race.get('heat')}"
        start_entry["starting_position"] = next_race_position

        logging.debug(
            f"Next round:{next_race_count} current rank:{previous_round_rank}"
        )
        logging.debug(
            f"Next:{next_race_heat} pos:{next_race_position}, id: {start_entry['race_id']}"
        )
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
