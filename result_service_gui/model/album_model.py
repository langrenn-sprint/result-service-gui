"""Album data class module."""

from marshmallow import fields, post_load, Schema

from .changelog import Changelog


class Album:
    """Basic model class."""

    def __init__(
        self,
        g_id,
        sync_on,
        event_id,
        camera_position,
        changelog,
        cover_photo_url,
        id,
        last_sync_time,
        place,
        title,
    ) -> None:
        """Init class."""
        self.g_id = g_id
        self.sync_on = sync_on
        self.event_id = event_id
        self.camera_position = camera_position
        self.changelog = changelog
        self.cover_photo_url = cover_photo_url
        self.id = id
        self.last_sync_time = last_sync_time
        self.place = place
        self.title = title


class AlbumSchema(Schema):
    """Album data class."""

    camera_position = fields.String(allow_none=True)
    g_id = fields.String(
        required=True, error_messages={"required": "Google album id is required."}
    )
    sync_on = fields.Boolean(default=True)
    event_id = fields.String()
    changelog = fields.Nested(Changelog(many=True), allow_none=True)
    cover_photo_url = fields.String(allow_none=True)
    id = fields.String()
    last_sync_time = fields.DateTime(allow_none=True)
    place = fields.String(allow_none=True)
    title = fields.String(allow_none=True)

    @post_load
    def make_user(self, data, **kwargs: str) -> Album:
        """Post load to return model class."""
        return Album(**data)
