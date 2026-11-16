import enum
import uuid
from dataclasses import field

import marshmallow_dataclass
from marshmallow import EXCLUDE, pre_load

from te_schemas import SchemaBase


class AlgorithmRunMode(enum.Enum):
    NOT_APPLICABLE = 0
    LOCAL = "local"
    REMOTE = "remote"
    BOTH = "both"


@marshmallow_dataclass.dataclass
class ExecutionScript(SchemaBase):
    class Meta:
        unknown = EXCLUDE

    id: uuid.UUID | str
    run_mode: AlgorithmRunMode | None = field(
        metadata={"by_value": True}, default=AlgorithmRunMode.NOT_APPLICABLE
    )
    name: str | None = field(default="")
    slug: str | None = field(default="")
    execution_callable: str | None = field(default="")
    version: str | None = field(default="")
    description: str | None = field(default="")
    name_readable: str | None = field(default="")
    additional_configuration: dict | None = None

    def __post_init__(self):  # ensure mutable default created safely
        if self.additional_configuration is None:
            self.additional_configuration = {}

    @pre_load
    def set_id_and_slug(self, data, **kwargs):
        if not data.get("slug"):
            data["slug"] = data.get("name", "").replace(" ", "-").lower()
            if data.get("version"):
                data["slug"] = data["slug"] + "-" + data["version"].replace(".", "-")
        if not data.get("id"):
            if data.get("name"):
                data["id"] = data.get("name")
            elif data.get("slug"):
                data["id"] = data.get("slug")
            else:
                data["id"] = "unknown-" + str(uuid.uuid4())

        return data
