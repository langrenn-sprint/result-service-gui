"""Resource module for start resources."""
import logging

from aiohttp import web
import aiohttp_jinja2

from result_service_gui.services import (
    KjoreplanService,
    RaceclassesAdapter,
    RaceplansAdapter,
    StartAdapter,
)
from .utils import (
    check_login,
    get_enchiced_startlist,
    get_event,
    get_qualification_text,
)


class Start(web.View):
    """Class representing the start view."""

    async def get(self) -> web.Response:
        """Get route function that return the startlister page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            informasjon = ""
            startliste = []
            races = []
            kjoreplan = []
            colseparators = []
            colclass = "w3-half"

            try:
                valgt_klasse = self.request.rel_url.query["klasse"]
            except Exception:
                valgt_klasse = ""  # noqa: F841
                informasjon = "Velg klasse for å se startlister."

            raceclasses = await RaceclassesAdapter().get_raceclasses(
                user["token"], event_id
            )

            if valgt_klasse == "live":
                # vis heat som starter nå
                colclass = "w3-third"
                iantallheat = 10
                isplitt = [3, 6]
                kjoreplan = await KjoreplanService().get_upcoming_heat(
                    self.request.app["db"], iantallheat
                )
                i = 0
                for heat in kjoreplan:
                    logging.debug(heat["Index"])
                    _liste = await StartAdapter().get_all_starts(
                        user["token"], event_id
                    )
                    if i in isplitt:
                        colseparators.append(heat["Index"])
                        logging.debug(colseparators)
                    i += 1
                    for loper in _liste:
                        startliste.append(loper)
                    logging.debug(startliste)
            else:
                # get startlister for klasse
                raceplans = await RaceplansAdapter().get_all_raceplans(
                    user["token"], event_id
                )
                if len(raceplans) > 0:
                    _tmp_races = raceplans[0]["races"]
                    if len(_tmp_races) == 0:
                        informasjon = f"{informasjon} Ingen kjøreplaner funnet."
                    else:
                        for race in _tmp_races:
                            if race["raceclass"] == valgt_klasse:
                                race["next_race"] = get_qualification_text(race)
                                race["start_time"] = race["start_time"][-8:]
                                races.append(race)

                        startliste = await get_enchiced_startlist(
                            user["token"], event_id, valgt_klasse
                        )

            """Get route function."""
            return await aiohttp_jinja2.render_template_async(
                "start.html",
                self.request,
                {
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "valgt_klasse": valgt_klasse,
                    "colseparators": colseparators,
                    "colclass": colclass,
                    "raceclasses": raceclasses,
                    "races": races,
                    "kjoreplan": [],
                    "startliste": startliste,
                    "username": user["name"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
