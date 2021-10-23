import typing
import binascii
import base64
import enum
import pathlib
import dataclasses

import marshmallow
import marshmallow_dataclass
from marshmallow_enum import EnumField

from . import SchemaBase


class PathField(marshmallow.fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        return pathlib.Path(value)


Path = marshmallow_dataclass.NewType("Path", str, field=PathField)


class JobResultType(enum.Enum):
    CLOUD_RESULTS = "CloudResults"
    LOCAL_RESULTS = "LocalResults"
    TIME_SERIES_TABLE = "TimeSeriesTable"


@marshmallow_dataclass.dataclass
class JobBand(SchemaBase):
    metadata: dict
    name: str
    no_data_value: typing.Optional[float] = dataclasses.field(default=-32768.0)
    activated: typing.Optional[bool] = dataclasses.field(default=True)
    add_to_map: typing.Optional[bool] = dataclasses.field(default=True)


@marshmallow_dataclass.dataclass
class JobUrl:
    url: str
    md5_hash: str = dataclasses.field(metadata={'data_key': 'md5Hash'})

    @property
    def decoded_md5_hash(self):
        return binascii.hexlify(base64.b64decode(self.md5_hash)).decode()


@marshmallow_dataclass.dataclass
class JobCloudResults:
    class Meta:
        unknown = 'EXCLUDE'

    name: str
    bands: typing.List[JobBand]
    urls: typing.List[JobUrl]
    data_path: typing.Optional[Path] = dataclasses.field(default=None)
    other_paths: typing.List[Path] = dataclasses.field(default_factory=list)
    type: JobResultType = dataclasses.field(
        default=JobResultType.CLOUD_RESULTS,
        metadata={"by_value": True}
    )


@marshmallow_dataclass.dataclass
class JobLocalResults:
    class Meta:
        unknown = 'EXCLUDE'

    name: str
    bands: typing.List[JobBand]
    data_path: typing.Optional[Path] = dataclasses.field(default=None)
    other_paths: typing.List[Path] = dataclasses.field(default_factory=list)
    type: JobResultType = dataclasses.field(
        default=JobResultType.LOCAL_RESULTS,
        metadata={"by_value": True}
    )


@marshmallow_dataclass.dataclass
class TimeSeriesTableResult:
    class Meta:
        unknown = 'EXCLUDE'

    name: str
    table: typing.List[dict]
    type: JobResultType = dataclasses.field(
        default=JobResultType.TIME_SERIES_TABLE,
        metadata={"by_value": True}
    )
