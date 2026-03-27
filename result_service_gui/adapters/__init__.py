"""Package for all services."""

from .albums_adapter import AlbumsAdapter
from .competition_format_adapter import CompetitionFormatAdapter
from .config_adapter import ConfigAdapter
from .contestants_adapter import ContestantsAdapter
from .events_adapter import EventsAdapter
from .photos_adapter import PhotosAdapter
from .raceclass_result_adapter import RaceclassResultsAdapter
from .raceclasses_adapter import RaceclassesAdapter
from .raceplans_adapter import RaceplansAdapter
from .result_adapter import ResultAdapter
from .start_adapter import StartAdapter
from .status_adapter import StatusAdapter
from .time_events_adapter import TimeEventsAdapter
from .user_adapter import UserAdapter

__all__ = [
    "AlbumsAdapter",
    "CompetitionFormatAdapter",
    "ConfigAdapter",
    "ContestantsAdapter",
    "EventsAdapter",
    "PhotosAdapter",
    "RaceclassResultsAdapter",
    "RaceclassesAdapter",
    "RaceplansAdapter",
    "ResultAdapter",
    "StartAdapter",
    "StatusAdapter",
    "TimeEventsAdapter",
    "UserAdapter",
]
