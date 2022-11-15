"""Module for raceclass results adapter."""
import logging

from .contestants_adapter import ContestantsAdapter
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

        # generate new resultset
        raceclass_result = await get_results_by_raceclass(token, event_id, valgt_klasse)

        # query contestant object to add ageclass
        contestants = await ContestantsAdapter().get_all_contestants_by_raceclass(
            token, event_id, valgt_klasse
        )
        for racer in raceclass_result["ranking_sequence"]:
            for contestant in contestants:
                if contestant["bib"] == racer["bib"]:
                    racer["ageclass"] = contestant["ageclass"]
                    break

        # and store to db
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
                        for rank_event in finish_ranks:
                            if rank_event["status"] == "OK":
                                rank_event[
                                    "club_logo"
                                ] = EventsAdapter().get_club_logo_url(
                                    rank_event["club"]
                                )
                                finish_rank.append(rank_event)

            # get the racers not finishing DNS - if results are official
            if race["results"]["Finish"]["status"] == 2:
                for start_entry in race["start_entries"]:
                    found_rank = False
                    for rank_entry in finish_rank:
                        if start_entry["bib"] == rank_entry["bib"]:
                            found_rank = True
                    if not found_rank:
                        dns_rank = {
                            "bib": start_entry["bib"],
                            "time_event": start_entry,
                            "name": start_entry["name"],
                            "club": start_entry["club"],
                            "status": "DNF",
                            "next_race_id": "",
                            "club_logo": EventsAdapter().get_club_logo_url(start_entry["club"]),
                        }
                        finish_rank.append(dns_rank)

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
        "FB1": [],
        "FB2": [],
        "FB3": [],
        "SA": [],
        "FC": [],
        "FC1": [],
        "FC2": [],
        "FC3": [],
        "FC4": [],
        "SC": [],
        "DNF": [],
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
                        "bib": _tmp_result["bib"],
                        "round": f"{race['round']}{race['index']}",
                        "name": _tmp_result["name"],
                        "club": _tmp_result["club"],
                        "club_logo": _tmp_result["club_logo"],
                        "ageclass": "",
                        "time_event": _tmp_result,
                    }
                    if _tmp_result["status"] == "DNF":
                        new_result["round"] = "DNF"
                        grouped_results["DNF"].append(new_result)
                    else:
                        grouped_results[f"{race['round']}{race['index']}"].append(
                            new_result
                        )

    # now - get the order and rank right
    ranking = 1
    racers_count = 0
    for round_res in grouped_results:
        for one_res in grouped_results[round_res]:
            if one_res["round"] != "DNF":
                one_res["rank"] = ranking
            results["ranking_sequence"].append(one_res)  # type: ignore
            racers_count += 1
            if one_res["round"].startswith("F"):
                ranking += 1
        else:
            ranking = racers_count + 1
    results["no_of_contestants"] = racers_count

    return results
