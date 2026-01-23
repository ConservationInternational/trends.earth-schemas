import dataclasses
import datetime
import enum
import re
import typing
import uuid

import marshmallow_dataclass
from marshmallow import post_load, pre_load

from .algorithms import ExecutionScript
from .results import (
    EmptyResults,
    FileResults,
    JsonResults,
    LocalPath,
    RasterResults,
    TimeSeriesTableResult,
    VectorResults,
)


class ScriptStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    BUILDING = "BUILDING"


class JobStatus(enum.Enum):
    READY = "READY"
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DELETED = "DELETED"
    DOWNLOADED = "DOWNLOADED"
    GENERATED_LOCALLY = "GENERATED_LOCALLY"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@marshmallow_dataclass.dataclass
class RemoteScript:
    id: uuid.UUID
    name: str
    slug: str
    description: str
    status: ScriptStatus = dataclasses.field(metadata={"by_value": True})
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user_id: uuid.UUID
    public: bool
    cpu_reservation: typing.Optional[int]
    cpu_limit: typing.Optional[int]
    memory_reservation: typing.Optional[int]
    memory_limit: typing.Optional[int]

    @post_load
    def set_timezone(self, data, **kwargs):
        data["created_at"] = data["created_at"].replace(tzinfo=datetime.timezone.utc)
        data["updated_at"] = data["updated_at"].replace(tzinfo=datetime.timezone.utc)

        return data


@marshmallow_dataclass.dataclass
class JobLocalContext:
    base_dir: LocalPath = dataclasses.field(default=None)
    area_of_interest_name: str = dataclasses.field(default="unknown-area")


# Type alias for a single result
SingleResult = typing.Union[
    RasterResults,
    FileResults,
    JsonResults,
    TimeSeriesTableResult,
    VectorResults,
    EmptyResults,
]


@marshmallow_dataclass.dataclass
class Job:
    id: uuid.UUID
    params: dict
    progress: int
    start_date: datetime.datetime
    status: JobStatus = dataclasses.field(metadata={"by_value": True})
    local_context: typing.Optional[JobLocalContext] = dataclasses.field(
        default_factory=JobLocalContext
    )
    # Results can be a single result object or a list of result objects
    results: typing.Optional[
        typing.Union[
            SingleResult,
            typing.List[SingleResult],
        ]
    ] = dataclasses.field(default_factory=dict)
    task_name: typing.Optional[str] = None
    task_notes: typing.Optional[str] = None
    script: typing.Optional[ExecutionScript] = None
    end_date: typing.Optional[datetime.datetime] = None
    user_id: typing.Optional[uuid.UUID] = None

    @pre_load
    def set_script_name_version(self, data, **kwargs):
        script_id = data.pop("script_id", None)
        params_script = None
        if "params" in data and data["params"] is not None:
            params_script = data["params"].pop("script", None)

        if not data.get("script"):
            if params_script:
                # Handle case where params_script could be a string (script ID) or dict (script object)
                if isinstance(params_script, str):
                    # It's just a script ID, create ExecutionScript object
                    data["script"] = ExecutionScript.Schema().dump(
                        ExecutionScript(id=params_script, name=str(params_script))
                    )
                else:
                    # It's a script object dictionary
                    data["script"] = params_script
            elif script_id:
                # Use script_id as both id and name for meaningful display
                data["script"] = ExecutionScript.Schema().dump(
                    ExecutionScript(id=script_id, name=str(script_id))
                )
            else:
                data["script"] = ExecutionScript.Schema().dump(
                    ExecutionScript(id="unknown-script", name="Unknown script")
                )

        # Ensure data["script"] is a dictionary before accessing its properties
        if isinstance(data["script"], dict):
            script_name_regex = re.compile("([0-9a-zA-Z -]*)(?: *)([0-9]+(_[0-9]+)+)")
            matches = script_name_regex.search(data["script"].get("name", ""))

            if matches:
                data["script"]["name"] = matches.group(1).rstrip()
                data["script"]["version"] = matches.group(2).replace("_", ".")

        return data

    @pre_load
    def set_main_fields_from_params(self, data, **kwargs):
        field_names = ["task_name", "task_notes", "local_context"]

        for field_name in field_names:
            field_value = None

            if field_name in data["params"]:
                field_value = data["params"].pop(field_name)

            if not data.get(field_name) and field_value:
                data[field_name] = field_value

        return data

    @post_load
    def set_timezone(self, data, **kwargs):
        data["start_date"] = data["start_date"].replace(tzinfo=datetime.timezone.utc)

        if data["end_date"]:
            data["end_date"] = data["end_date"].replace(tzinfo=datetime.timezone.utc)

        return data

    @property
    def visible_name(self) -> str:
        if self.script is not None:
            if self.script.name:
                script_name = self.script.name
            else:
                script_name = self.script.name_readable
        else:
            script_name = ""

        if self.task_name and script_name:
            name = f"{self.task_name} ({script_name})"
        elif self.task_name:
            name = self.task_name + " (unknown script)"
        elif script_name:
            name = script_name + " (unnamed task)"
        else:
            name = "Unnamed task (unknown script)"

        return name

    def _get_results_list(self) -> typing.List[SingleResult]:
        """Return results as a list, whether it's a single result or already a list."""
        if self.results is None:
            return []
        if isinstance(self.results, list):
            return self.results
        return [self.results]

    def is_file(self) -> bool:
        """Check if any result is a FileResults."""
        return any(isinstance(r, FileResults) for r in self._get_results_list())

    def is_vector(self) -> bool:
        """Check if any result is a VectorResults."""
        return any(isinstance(r, VectorResults) for r in self._get_results_list())

    def is_raster(self) -> bool:
        """Check if any result is a RasterResults."""
        return any(isinstance(r, RasterResults) for r in self._get_results_list())

    def get_results_by_type(self, result_type: type) -> typing.List[SingleResult]:
        """Get all results of a specific type."""
        return [r for r in self._get_results_list() if isinstance(r, result_type)]

    def get_first_result_by_type(
        self, result_type: type
    ) -> typing.Optional[SingleResult]:
        """Get the first result of a specific type, or None if not found."""
        results = self.get_results_by_type(result_type)
        return results[0] if results else None
