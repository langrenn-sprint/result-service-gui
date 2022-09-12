"""Module for raceclass results adapter."""
import logging

from .events_adapter import EventsAdapter
from .raceclass_result_adapter import RaceclassResultsAdapter
from .raceplans_adapter import RaceplansAdapter


class RaceclassResultsService:
    """Class representing raceclasses."""

    async def create_raceclass_results(
        self, token: str, event_id: str, valgt_klasse: str
    ) -> int:
        """Create or recreate raceclass results function."""
        # first delete any old results
        try:
            resultlist = await RaceclassResultsAdapter().get_raceclass_result(
                event_id, valgt_klasse
            )
            if resultlist:
                res = await RaceclassResultsAdapter().delete_raceclass_result(
                    token, event_id, valgt_klasse
                )
                logging.debug(
                    f"Deleted old results for raceclass {valgt_klasse} - {res}"
                )
        except Exception:
            logging.debug(f"No results found, no delete required {valgt_klasse}")

        # generate new result and store
        raceclass_result = await get_results_by_raceclass(token, event_id, valgt_klasse)
        res = await RaceclassResultsAdapter().create_raceclass_results(
            token, event_id, raceclass_result
        )
        return res

    def get_finish_rank_for_race(self, race: dict) -> list:
        """Extract timing events from finish and append club logo."""
        finish_rank = []
        results = race["results"]
        if len(results) > 0:
            logging.debug(f"Resultst: {results}")
            if "Finish" in results.keys():
                finish_results = results["Finish"]
                if len(finish_results) > 0:
                    if "ranking_sequence" in finish_results.keys():
                        finish_ranks = finish_results["ranking_sequence"]
                        race["finish_results"] = []
                        for rank_event in finish_ranks:
                            if rank_event["status"] == "OK":
                                rank_event[
                                    "club_logo"
                                ] = EventsAdapter().get_club_logo_url(
                                    rank_event["club"]
                                )
                                finish_rank.append(rank_event)
        return finish_rank


async def get_results_by_raceclass(
    token: str, event_id: str, valgt_klasse: str
) -> dict:
    """Get results for raceclass - return sorted list."""
    results = {
        "event_id": event_id,
        "raceclass": valgt_klasse,
        "timing_point": "Finish",
        "no_of_contestants": 0,
        "ranking_sequence": [],
        "status": 1,
    }
    grouped_results = {  # type: ignore
        "FA": [],
        "FB": [],
        "SA": [],
        "FC": [],
        "SC": [],
    }
    races = await RaceplansAdapter().get_races_by_racesclass(
        token, event_id, valgt_klasse
    )
    # first - extract all result-items
    for race in races:
        # need results for A final - exit if not
        if race["round"] == "F" and race["index"] == "A":
            if len(race["results"]) == 0:
                return {}
        # skip results from qualification
        if race["round"] != "Q":
            race_details = await RaceplansAdapter().get_race_by_id(token, race["id"])
            finish_results = RaceclassResultsService().get_finish_rank_for_race(
                race_details
            )
            for _tmp_result in finish_results:
                # skip results if racer has more races
                if _tmp_result["next_race_id"] == "":
                    new_result: dict = {
                        "rank": 0,
                        "bib": _tmp_result["bib"],
                        "round": f"{race['round']}{race['index']}",
                        "name": _tmp_result["name"],
                        "club": _tmp_result["club"],
                        "club_logo": _tmp_result["club_logo"],
                        "ageclass": "",
                        "time_event": _tmp_result,
                    }
                    grouped_results[f"{race['round']}{race['index']}"].append(
                        new_result
                    )

    # now - get the order and rank right
    ranking = 1
    racers_count = 0
    for round_res in grouped_results:
        for one_res in grouped_results[round_res]:
            one_res["rank"] = ranking
            results["ranking_sequence"].append(one_res)  # type: ignore
            racers_count += 1
            if one_res["round"].startswith("F"):
                ranking += 1
        else:
            ranking = racers_count + 1
    results["no_of_contestants"] = racers_count

    return results
