"""Album data class module."""
from marshmallow import fields, post_load, Schema


class Race:
    """Basic model class."""
    def __init__(
        self,
        id,
        raceclass,
        round,
        index,
        heat,
        order,
        start_time,
        max_no_of_contestants,
        next_round_info,
        no_of_contestants,
        photos,
        event_id,
        raceplan_id,
        start_entries,
        finish_results,
        results
    ) -> None:
        """Init class."""
        self.id = id
        self.raceclass = raceclass
        self.round = round
        self.index = index
        self.heat = heat
        self.order = order
        self.start_time = start_time
        self.max_no_of_contestants = max_no_of_contestants
        self.next_round_info = next_round_info
        self.no_of_contestants = no_of_contestants
        self.photos = photos
        self.event_id = event_id
        self.raceplan_id = raceplan_id
        self.start_entries = start_entries
        self.finish_results = finish_results
        self.results = results


class RaceSchema(Schema):
    """Schema data class."""
    id = fields.String()
    raceclass = fields.String()
    round = fields.String()
    index = fields.String()
    heat = fields.String()
    order = fields.Integer()
    start_time = fields.DateTime()
    max_no_of_contestants = fields.Integer()
    next_round_info = fields.String()
    no_of_contestants = fields.Integer()
    photos = fields.List(fields.Dict())
    event_id = fields.String()
    raceplan_id = fields.String()
    start_entries = fields.List(fields.String())
    finish_results = fields.List(fields.Dict())
    results = fields.Dict(fields.String(), fields.String())

    @post_load
    def make_user(self, data, **kwargs: str) -> Race:
        """Post load to return model class."""
        return Race(**data)
