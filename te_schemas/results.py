import dataclasses
import enum
import pathlib
import re
import typing
from dataclasses import field

import marshmallow_dataclass
from marshmallow import fields
from marshmallow import validate
from marshmallow_dataclass.typing import Url


class PathField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match(r"/vsi(s3)|(gs)", str(value)) is not None:
            # Don't convert direction of slashes for GDAL vsi uris, as will
            # confuse GDAL

            return pathlib.PurePosixPath(value)
        else:
            return pathlib.Path(value)


Path = marshmallow_dataclass.NewType("Path", str, field=PathField)


class DataType(enum.Enum):
    BYTE = "Byte"
    UINT16 = "UInt16"
    INT16 = "Int16"
    UINT32 = "UInt32"
    INT32 = "Int32"
    FLOAT32 = "Float32"
    FLOAT64 = "Float64"


class RasterFileType(enum.Enum):
    GEOTIFF = "GeoTiff"
    COG = "COG"


class EtagType(enum.Enum):
    AWS = "AWS MD5 Etag"
    AWS_Multipart = "AWS Multipart Etag"
    GCS_CRC32C = "GCS CRC32C Etag"
    GCS_MD5 = "GCS MD5 Etag"


@marshmallow_dataclass.dataclass
class Etag():
    hash: str
    type: EtagType = dataclasses.field(metadata={"by_value": True})


@marshmallow_dataclass.dataclass
class URI():
    type: str = field(metadata={'validate': validate.OneOf(["local", "url"])})
    uri: typing.Union[Path, Url]
    etag: typing.Optional[Etag]


@marshmallow_dataclass.dataclass
class Band():
    name: str
    metadata: dict
    no_data_value: typing.Union[int, float] = -32768
    add_to_map: bool = False
    activated: bool = True


@marshmallow_dataclass.dataclass
class Raster():
    datatype: DataType = dataclasses.field(metadata={"by_value": True})
    filetype: RasterFileType = dataclasses.field(metadata={"by_value": True})
    bands: typing.List[Band]
    uri: typing.List[URI]


@marshmallow_dataclass.dataclass
class CloudResultsV2():
    name: str
    data: typing.List[Raster]
