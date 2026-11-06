"""Utilities module for gui services."""

import logging
from datetime import datetime
from typing import NoReturn
from urllib.parse import urlencode, urlsplit

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.adapters import (
    ContestantsAdapter,
    EventsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    UserAdapter,
)
from result_service_gui.services import (
    RaceclassResultsService,
)

# Pages that must not be the target of a redirect after login.
_NO_NEXT_PATHS = ("/login", "/logout")
ADMIN_ROLE = "admin"


def safe_next_path(value: str | None) -> str | None:
    """Return value if it is a safe relative path to redirect to, else None.

    Only paths on this site are allowed ("/timing?event_id=1"), to avoid an
    open redirect. Rejected: absolute and scheme-relative URLs ("//host"),
    backslashes and control characters (browsers may turn a path with those
    into "//host"), and the login and logout pages.
    """
    if not value or not value.startswith("/") or value.startswith("//"):
        return None
    if "\\" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return None
    if parts.path.rstrip("/") in _NO_NEXT_PATHS:
        return None
    return value


def login_location(informasjon: str, next_path: str | None = None) -> str:
    """Return the login page URL, with next= if next_path is safe."""
    query = {"informasjon": informasjon}
    safe_next = safe_next_path(next_path)
    if safe_next:
        query["next"] = safe_next
    return f"/login?{urlencode(query)}"


UNEXPECTED_ERROR = "Det har oppstått en uventet feil. Feilen er logget."
LOGIN_AGAIN = "Innloggingen er utløpt. Logg inn på nytt."


def is_login_error(e: Exception) -> bool:
    """Return True if the error is a missing or expired login (401).

    The adapters report 401 as "401 Unathorized - …" or "Login expired: …".
    """
    text = str(e.reason) if isinstance(e, web.HTTPException) else str(e)
    return text.startswith("401") or "Login expired" in text


def error_text(e: Exception) -> str:
    """Return a message for the user about an error.

    Errors from our own code (plain Exception) and from the backend services
    (HTTP errors from the adapters) carry a message for the user. Other errors,
    e.g. TypeError, are programming errors: the user gets a general message,
    and the details are only logged.
    """
    if isinstance(e, web.HTTPException):
        return f"Det har oppstått en feil: {e.reason}"
    if type(e) is Exception:
        return f"Det har oppstått en feil: {e}"
    return UNEXPECTED_ERROR


def raise_error(view: web.View, e: Exception, location: str = "/") -> NoReturn:
    """Handle an error in a view: log it, and send the user on with a message.

    Redirects raised in the view, e.g. to the login page, pass through. A
    missing or expired login sends the user to the login page, and back to
    the page after login. Any other error sends the user to `location` with a
    message: the user is still logged in.
    """
    if isinstance(e, web.HTTPRedirection):
        raise e
    request = view.request
    logging.error("Error in %s %s", request.method, request.path_qs, exc_info=e)
    if is_login_error(e):
        raise web.HTTPSeeOther(
            location=login_location(LOGIN_AGAIN, request.path_qs)
        ) from e
    query = urlencode({"informasjon": error_text(e)})
    raise web.HTTPSeeOther(location=f"{location}?{query}") from e


def error_message(view: web.View, e: Exception) -> str:
    """Handle an error in a view where the user stays on the page.

    Like raise_error, but returns the message for the page instead of
    redirecting: redirects pass through, the error is logged, and a missing
    or expired login sends the user to the login page.
    """
    if isinstance(e, web.HTTPRedirection):
        raise e
    request = view.request
    logging.error("Error in %s %s", request.method, request.path_qs, exc_info=e)
    if is_login_error(e):
        raise web.HTTPSeeOther(
            location=login_location(LOGIN_AGAIN, request.path_qs)
        ) from e
    return error_text(e)


async def check_login(self) -> dict:
    """Check login and return user credentials.

    A user that is not logged in, or whose token has expired, is sent to the
    login page, and back to this page after login.
    """
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        raise web.HTTPSeeOther(
            location=login_location(informasjon, self.request.path_qs)
        )

    return {
        "name": session["name"],
        "loggedin": True,
        "token": session["token"],
        "role": session.get("role", ""),
    }


async def check_login_open(self) -> dict:
    """Check login and return credentials."""
    user = {}
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if loggedin:
        user = {
            "name": session["name"],
            "loggedin": True,
            "token": session["token"],
        }
    else:
        user = {"name": "Gjest", "loggedin": False, "token": ""}

    return user


def get_display_style(start_time: str, event: dict) -> str:
    """Calculate time remaining to start and return table header style."""
    time_now = EventsAdapter().get_local_datetime_now(event)
    start_time_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
    # make sure timezone is correct
    start_time_obj = start_time_obj.replace(tzinfo=time_now.tzinfo)
    delta_time = start_time_obj - time_now
    delta_seconds = delta_time.total_seconds()
    display_style = ""
    if delta_seconds < 300:
        display_style = "table_header_green"
    elif delta_seconds < 600:
        display_style = "table_header_orange"
    else:
        display_style = "headerblue"

    return display_style


def get_startlist_with_logos(race: dict) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    if race["start_entries"]:
        for start_entry in race["start_entries"]:
            start_entry["club_logo"] = EventsAdapter().get_club_logo_url(
                start_entry["club"]
            )
            startlist.append(start_entry)
    return startlist


async def get_enrichced_startlist(user: dict, race: dict) -> list:
    """Enrich startlist information - including info if race result is registered."""
    startlist = []
    i = 0
    # get time-events registered
    next_race_time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race["id"]
    )
    if race["start_entries"]:
        for start_entry in race["start_entries"]:
            start_entry["club_logo"] = EventsAdapter().get_club_logo_url(
                start_entry["club"]
            )
            i += 1
            for time_event in next_race_time_events:
                # get next race info
                if time_event["timing_point"] == "Template":
                    logging.debug(f"Time_event with error - {time_event}")
                elif time_event["timing_point"] == "Template":
                    if i == time_event["rank"]:
                        if time_event["next_race"].startswith("Ute"):
                            start_entry["next_race"] = "Ute"
                        else:
                            start_entry["next_race"] = time_event["next_race"]
                # check if start, DNS or DNF is registered
                elif time_event["timing_point"] in ["Start", "DNS", "DNF"]:
                    if time_event["bib"] == start_entry["bib"]:
                        start_entry["status"] = time_event["timing_point"]
                        start_entry["status_id"] = time_event["id"]
            startlist.append(start_entry)
    return startlist


async def get_finish_timings(user: dict, race_id: str) -> list:
    """Get finish events for race, Template event if no result is registered."""
    finish_events = []
    race = await RaceplansAdapter().get_race_by_id(user["token"], race_id)

    # get time-events registered
    time_events = await TimeEventsAdapter().get_time_events_by_race_id(
        user["token"], race_id
    )
    found_events = 0
    for i in range(1, race["max_no_of_contestants"] + 1):
        for time_event in time_events:
            if time_event["timing_point"] == "Finish" and time_event["status"] == "OK":
                if i == time_event["rank"]:
                    found_events += 1
                    finish_events.append(time_event)
        if found_events == 0:
            if race["round"] == "F":
                dummy_event = {"rank": i}
                finish_events.append(dummy_event)
            else:
                for time_event in time_events:
                    if (time_event["timing_point"] == "Template") and (
                        i == time_event["rank"]
                    ):
                        finish_events.append(time_event)
                        break
        else:
            found_events = found_events - 1
    return finish_events


async def get_event(user: dict, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Langrenn-sprint", "organiser": "Ikke valgt"}
    if event_id:
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(user["token"], event_id)

    return event


async def get_passeringer(
    token: str, event_id: str, action: str, valgt_klasse: str
) -> list:
    """Return list of passeringer for selected action."""
    passeringer = []
    _tmp_passeringer = await TimeEventsAdapter().get_time_events_by_event_id(
        token, event_id
    )

    # filter based upon raceclass
    tmp_passeringer = []
    for passering in _tmp_passeringer:
        if passering["race"].startswith(valgt_klasse):
            tmp_passeringer.append(passering)

    if action == "control":
        for passering in reversed(tmp_passeringer):
            if not valgt_klasse or valgt_klasse in passering["race"]:
                if (
                    passering["status"] == "Error"
                    and passering["timing_point"] != "Template"
                ):
                    passeringer.append(passering)
    elif action in ["Template", "DNS"]:
        for passering in tmp_passeringer:
            if valgt_klasse in passering["race"]:
                if passering["timing_point"] == action:
                    passeringer.append(passering)
    else:
        for passering in tmp_passeringer:
            if passering["timing_point"] not in [
                "Template",
                "Error",
            ]:
                passeringer.append(passering)

    # indentify last passering in race
    i = 0
    last_race = ""
    for passering in passeringer:
        if i == 0:
            passering["first_in_heat"] = True
        elif last_race != passering["race"]:
            passeringer[i - 1]["last_in_heat"] = True
            passering["first_in_heat"] = True
        i += 1
        if i == len(passeringer):
            passering["last_in_heat"] = True
        last_race = passering["race"]

    # sort by time
    def myfunc(n) -> str:
        return n["registration_time"]

    passeringer.sort(key=myfunc)
    passeringer.reverse()

    return passeringer


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    if race["round"] == "R1":
        text = "Alle til runde 2"
    elif race["round"] in ["R2", "F"]:
        text = ""
    else:
        for key, value in race["rule"].items():
            if key == "S":
                for x, y in value.items():
                    if y == "REST":
                        text += f"Resten til semi {x}. "
                    elif y > 0:
                        text += f"{y} til semi {x}. "
            elif key == "F":
                for x, y in value.items():
                    if y == "ALL":
                        text += f"Alle til finale {x}. "
                    elif y == "REST":
                        text += f"Resten til finale {x}. "
                    elif y > 0:
                        text += f"{y} til finale {x}. "
    logging.debug(f"Regel hele: {text}")
    return text


async def get_race_id_by_name(
    user: dict, event_id: str, next_race: str, raceclass: str
) -> str:
    """Get race_id for a given race."""
    race_id = ""
    races = await RaceplansAdapter().get_races_by_racesclass(
        user["token"], event_id, raceclass
    )
    for race in races:
        tmp_next_race = f"{race['round']}{race['index']}{race['heat']}"
        if next_race == tmp_next_race:
            return race["id"]
    return race_id


def get_raceplan_summary(races: list, raceclasses: list) -> list:
    """Generate a summary with key timing for the raceplan."""
    summary = []
    # create a dict of all raceclasses and populate
    # loop raceclasses and find key parameters
    for raceclass in raceclasses:
        class_summary = {"name": raceclass["name"]}
        class_summary["no_of_contestants"] = raceclass["no_of_contestants"]
        class_summary["ranking"] = raceclass["ranking"]
        # loop through races - update start time pr round pr class
        for race in reversed(races):
            if race["raceclass"] == raceclass["name"]:
                if race["round"] in ["Q", "R1"]:
                    class_summary["timeQ"] = race["start_time"][-8:]
                    class_summary["orderQ"] = race["order"]
                elif race["round"] in ["S", "R2"]:
                    class_summary["timeS"] = race["start_time"][-8:]
                    class_summary["orderS"] = race["order"]
                elif race["round"] == "F":
                    class_summary["timeF"] = race["start_time"][-8:]
                    class_summary["orderF"] = race["order"]
        summary.append(class_summary)
    logging.debug(summary)
    return summary


async def get_races_for_live_view(
    user: dict, event: dict, races: list, valgt_heat: int, number_of_races: int
) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    i = 0
    time_now = EventsAdapter().get_local_time(event, "log")
    # find next race on start
    if valgt_heat == 0:
        for race in races:
            if time_now < race["start_time"]:
                valgt_heat = race["order"]
                break
        else:
            if valgt_heat == 0:
                # all races have already started
                valgt_heat = len(races) + 1

    for race in races:
        # from heat number (order) if selected
        if (race["order"] >= valgt_heat) and (i < number_of_races):
            race_detailed = await RaceplansAdapter().get_race_by_id(
                user["token"], race["id"]
            )
            filtered_racelist.append(race_detailed)
            i += 1

    return filtered_racelist


async def get_races_for_print(
    user: dict, _tmp_races: list, raceclasses: list, valgt_klasse: str, action: str
) -> list:
    """Get races with lists - formatted for print."""
    races = []
    for race in _tmp_races:
        for raceclass in raceclasses:
            if race["raceclass"] == raceclass["name"]:
                if (race["raceclass"] == valgt_klasse) or (valgt_klasse == ""):
                    race = await RaceplansAdapter().get_race_by_id(
                        user["token"], race["id"]
                    )
                    race["next_race"] = get_qualification_text(race)
                    race["start_time"] = race["start_time"][-8:]
                    # get start list details
                    if action == "live":
                        race["list_type"] = "start"
                        if race["results"]:
                            if "Finish" in race["results"]:
                                race["list_type"] = "result"
                    else:
                        race["list_type"] = action

                    if race["list_type"] == "start":
                        race["startliste"] = await get_enrichced_startlist(user, race)
                    else:
                        race["finish_results"] = (
                            RaceclassResultsService().get_finish_rank_for_race(
                                race, False
                            )
                        )
                    races.append(race)
    return races


async def get_races_for_round_result(
    user: dict, _tmp_races: list, valgt_runde: str, valgt_klasse: str, action: str
) -> list:
    """Get races for a given round - formatted for print."""
    races = []
    next_round = []
    if valgt_runde == "Q":
        next_round = ["S", "F"]
    elif valgt_runde == "S":
        next_round = ["F"]

    for race in _tmp_races:
        if race["raceclass"] == valgt_klasse:
            race = await RaceplansAdapter().get_race_by_id(user["token"], race["id"])
            race["start_time"] = race["start_time"][-8:]
            if valgt_runde in ["", race["round"]]:
                if action.count("result") > 0:
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "result"
                    race["finish_results"] = (
                        RaceclassResultsService().get_finish_rank_for_race(race, False)
                    )
                    races.append(race)
            elif race["round"] in next_round:
                if action.count("start") > 0:
                    race["next_race"] = get_qualification_text(race)
                    race["list_type"] = "start"
                    race["startliste"] = await get_enrichced_startlist(user, race)
                    races.append(race)
    return races


class InvalidStartError(Exception):
    """The start can not be added; the message tells the user why."""


START_ENTRY_FIELDS = (
    "startlist_id",
    "race_id",
    "bib",
    "starting_position",
    "scheduled_start_time",
    "name",
    "club",
)


async def create_start(user: dict, form: dict) -> str:
    """Add one start to the race in the form (Legg til)."""
    try:
        new_start, new_race = await prepare_start(user, form, form["race_id"])
    except InvalidStartError as e:
        return str(e)
    await StartAdapter().create_start_entry(user["token"], new_start)
    informasjon = f"Lagt til nr {new_start['bib']}."
    informasjon += await update_previous_result(user, form, new_start, new_race)
    return informasjon


async def move_start(user: dict, form: dict) -> str:
    """Move one start to the race chosen in the form (Flytt).

    Everything is checked before the start is deleted from its race. If adding
    it to the new race still fails, the start is put back where it was.
    """
    if not form.get("new_heat"):
        return "Velg nytt heat før du trykker Flytt."
    token = user["token"]
    old_start = await StartAdapter().get_start_entry_by_id(
        token, form["race_id"], form["start_id"]
    )
    try:
        new_start, new_race = await prepare_start(
            user, form, form["new_heat"], old_start
        )
    except InvalidStartError as e:
        return f"Ikke flyttet: {e}"
    await StartAdapter().delete_start_entry(token, form["race_id"], form["start_id"])
    try:
        await StartAdapter().create_start_entry(token, new_start)
    except Exception as e:
        await put_back_start(token, old_start, e)
        raise
    informasjon = f"Flyttet nr {new_start['bib']}."
    informasjon += await update_previous_result(user, form, new_start, new_race)
    return informasjon


async def put_back_start(token: str, old_start: dict, error: Exception) -> None:
    """Put a start back in its race after a failed move."""
    try:
        await StartAdapter().create_start_entry(
            token, {key: old_start[key] for key in START_ENTRY_FIELDS}
        )
    except Exception as e:
        logging.exception("Could not put back start after failed move")
        err_msg = (
            f"Flyttingen feilet, og nr {old_start['bib']} kunne ikke legges "
            "tilbake i heatet. Legg til nr på nytt."
        )
        raise Exception(err_msg) from e
    logging.warning(f"Move failed, start put back: {error}")


async def prepare_start(
    user: dict, form: dict, race_id: str, moving_start: dict | None = None
) -> tuple[dict, dict]:
    """Check the form and return the new start and the race it goes to.

    moving_start is the start being moved, if any: it is not counted when
    checking whether the bib is already in the round.
    Raises InvalidStartError if the start can not be added.
    """
    token = user["token"]
    event_id = form["event_id"]
    bib_text = str(form.get("bib", "")).strip()
    if not bib_text.isdigit():
        msg = "Fyll inn startnummer."
        raise InvalidStartError(msg)
    bib = int(bib_text)
    contestant = await ContestantsAdapter().get_contestant_by_bib(token, event_id, bib)
    if not contestant:
        msg = f"Fant ikke deltaker med startnr {bib}."
        raise InvalidStartError(msg)

    new_race = await RaceplansAdapter().get_race_by_id(token, race_id)
    start_entries = new_race.get("start_entries", [])
    max_contestants = new_race.get("max_no_of_contestants")
    if max_contestants is not None and len(start_entries) >= max_contestants:
        msg = "Heatet er fullt."
        raise InvalidStartError(msg)

    # the bib can only be in one race per round
    for start_entry in await StartAdapter().get_start_entries_by_bib(
        token, event_id, bib
    ):
        if moving_start and start_entry["id"] == moving_start["id"]:
            continue
        race = await RaceplansAdapter().get_race_by_id(token, start_entry["race_id"])
        if race["round"] == new_race["round"]:
            msg = f"Nr {bib} er allerede med i runde {race['round']}."
            raise InvalidStartError(msg)

    return {
        "startlist_id": await get_startlist_id(token, event_id, start_entries),
        "race_id": new_race["id"],
        "bib": bib,
        "starting_position": get_starting_position(form, start_entries),
        "scheduled_start_time": new_race["start_time"],
        "name": f"{contestant['first_name']} {contestant['last_name']}",
        "club": contestant["club"],
    }, new_race


def get_starting_position(form: dict, start_entries: list) -> int:
    """Return the position from the form, or the first free one in the race."""
    taken = {start_entry["starting_position"] for start_entry in start_entries}
    position_text = str(form.get("starting_position", "")).strip()
    if not position_text:
        return min(set(range(1, len(taken) + 2)) - taken)
    if not position_text.isdigit() or int(position_text) < 1:
        msg = "Posisjon må være et tall fra 1 og oppover."
        raise InvalidStartError(msg)
    position = int(position_text)
    if position in taken:
        msg = f"Posisjon {position} er opptatt."
        raise InvalidStartError(msg)
    return position


async def get_startlist_id(token: str, event_id: str, start_entries: list) -> str:
    """Return the id of the startlist that the race's starts belong to."""
    if start_entries:
        return start_entries[0]["startlist_id"]
    startlists = await StartAdapter().get_all_starts_by_event(token, event_id)
    if not startlists:
        msg = "Fant ingen startliste for arrangementet."
        raise InvalidStartError(msg)
    return startlists[0]["id"]


async def update_previous_result(
    user: dict, form: dict, new_start: dict, new_race: dict
) -> str:
    """Point the start's latest finish result to the new race (videre til)."""
    bib = new_start["bib"]
    time_events = await TimeEventsAdapter().get_time_events_by_event_id_and_bib(
        user["token"], form["event_id"], bib
    )
    latest_result: dict = {}
    for time_event in time_events:
        if (time_event["timing_point"] == "Finish") and (time_event["bib"] == bib):
            if (not latest_result) or (
                time_event["registration_time"] > latest_result["registration_time"]
            ):
                latest_result = time_event
    if not latest_result:
        return ""
    latest_result["next_race_id"] = new_race["id"]
    if new_race["round"] == "F":
        latest_result["next_race"] = f"{new_race['round']}{new_race['index']}"
    else:
        latest_result["next_race"] = (
            f"{new_race['round']}{new_race['index']}{new_race['heat']}"
        )
    latest_result["next_race_position"] = new_start["starting_position"]
    await TimeEventsAdapter().update_time_event(
        user["token"], latest_result["id"], latest_result
    )
    return " Oppdatert videre til fra forrige runde."


async def delete_start(user: dict, form: dict) -> str:
    """Extract form data and delete one start event."""
    await StartAdapter().delete_start_entry(
        user["token"], form["race_id"], form["start_id"]
    )
    return "Slettet start."


def get_foto_finish_for_race(race: dict, photos: list) -> list:
    """Loop throgh photos and return relevant finish photo(s)."""
    fotos = []
    for photo in photos:
        if photo["race_id"] == race["id"]:
            if photo["is_photo_finish"] and (photo["confidence"] > 80):
                fotos.append(photo)
    return fotos


async def get_race_kpis(
    token: str, event: dict, raceclasses: list, valgt_runde: str
) -> list:
    """Generate a summary with key performance indicators for race execution."""
    summary_kpis = []
    all_races = await RaceplansAdapter().get_all_races(token, event["id"])
    raceplan_summary = get_raceplan_summary(all_races, raceclasses)

    # enrich with race details
    for raceclass in raceplan_summary:
        races = await RaceplansAdapter().get_races_by_racesclass(
            token, event["id"], raceclass["name"]
        )
        races_q = []
        races_s = []
        races_f = []
        for race in races:
            # calculate key kpis pr race
            race_summary = get_race_summary(event, race)

            if (race["round"] in ["Q", "R1"]) and (valgt_runde in ["Q", "A"]):
                races_q.append(race_summary)
            elif (race["round"] in ["S", "R2"]) and (valgt_runde in ["S", "A"]):
                races_s.append(race_summary)
            elif (race["round"] == "F") and (valgt_runde in ["F", "A"]):
                races_f.append(race_summary)
        raceclass["races_q"] = races_q
        raceclass["races_s"] = races_s
        raceclass["races_f"] = races_f
        raceclass["progress"] = get_raceclass_progress(races_q, races_s, races_f)

        summary_kpis.append(raceclass)
    return summary_kpis


def get_raceclass_progress(races_q: list, races_s: list, races_f: list) -> int:
    """Calculate overal progress of race execution."""
    raceclass_progress = 1
    # 1 not started
    # 2 not started - with DNS */
    # 3 started - no results */
    # 4 partial results - with DNF */
    # 5 all results ok */
    # 6 error in race results */
    for race in races_f:
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    for race in races_s:
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    for race in races_q:
        raceclass_progress = max(raceclass_progress, race["progress"])
        if race["progress"] in [4, 6]:
            return race["progress"]  # partial or error results
    return raceclass_progress


def get_race_summary(event: dict, race: dict) -> dict:
    """Calculate key kpis for a single race."""
    try:
        count_starts = len(race["start_entries"])
    except Exception:
        count_starts = 0
    try:
        count_results = len(race["results"]["Finish"]["ranking_sequence"])
    except Exception:
        count_results = 0
    try:
        count_dns = len(race["results"]["DNS"]["ranking_sequence"])
    except Exception:
        count_dns = 0
    try:
        count_dnf = len(race["results"]["DNF"]["ranking_sequence"])
    except Exception:
        count_dnf = 0

    race_progress = get_race_progress(
        event, race, count_starts, count_dns, count_dnf, count_results
    )

    if event["competition_format"] != "Individual Sprint":
        race_name = event["competition_format"]
    elif race["round"] == "F":
        race_name = f"{race['round']}{race['index']}"
    else:
        race_name = f"{race['round']}{race['index']}{race['heat']}"

    return {
        "name": race_name,
        "order": race["order"],
        "count_starts": count_starts,
        "count_results": count_results,
        "count_dns": count_dns,
        "count_dnf": count_dnf,
        "progress": race_progress,
        "start_time": race["start_time"][-8:],
    }


def get_race_progress(  # noqa: PLR0917
    event: dict,
    race: dict,
    count_starts: int,
    count_dns: int,
    count_dnf: int,
    count_results: int,
) -> int:
    """Evaluate race progress and return a code to indicate coloring in dashboard."""
    progress = 6
    # 0 empty / no starts
    # 1 not started
    # 2 not started - with DNS */
    # 3 started - no results */
    # 4 partial results - with DNF */
    # 5 all results ok */
    # 6 error in race results */
    time_now = EventsAdapter().get_local_time(event, "log")
    start_time = race["start_time"]
    if count_starts == 0:
        progress = 0
    elif start_time > time_now:
        if count_results > 0 or count_dnf > 0:
            progress = 6
        elif count_dns == 0:
            progress = 1
        else:
            progress = 2
    elif count_results == 0:
        if count_starts == 0:
            progress = 5
        else:
            progress = 3
    elif (count_results + count_dns + count_dnf) < count_starts:
        progress = 4
    elif (count_results + count_dns + count_dnf) > count_starts:
        progress = 6
    else:
        progress = 5
    return progress
