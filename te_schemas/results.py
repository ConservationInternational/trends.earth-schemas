from __future__ import annotations

import base64
import binascii
import dataclasses
import enum
import pathlib
import typing

import marshmallow
import marshmallow_dataclass
from marshmallow import EXCLUDE
from marshmallow import fields
from marshmallow import validate
from marshmallow.exceptions import ValidationError
from marshmallow_dataclass.typing import Url


class PathValidator(validate.Regexp):
    def __call__(self, value):
        if self.regex.match(str(value)) is None:
            raise ValidationError(self._format_error(value))

        return value


class VSIPathField(fields.Field):
    def _serialize(self, value: pathlib.PurePosixPath, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value: dict, attr, data, **kwargs):
        return pathlib.PurePosixPath(value)


VSIPath = marshmallow_dataclass.NewType(
    "VSIPath",
    pathlib.PurePosixPath,
    validate=PathValidator(r"/vsi(s3)|(gs)"),
    field=VSIPathField,
)


class LocalPathField(fields.Field):
    def _serialize(self, value: pathlib.Path, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value: dict, attr, data, **kwargs):
        return pathlib.Path(value)


LocalPath = marshmallow_dataclass.NewType(
    "LocalPath", pathlib.Path, field=LocalPathField
)


class ResultType(enum.Enum):
    CLOUD_RESULTS = "CloudResults"
    RASTER_RESULTS = "RasterResults"
    FILE_RESULTS = "FileResults"
    TIME_SERIES_TABLE = "TimeSeriesTable"
    JSON_RESULTS = "JsonResults"
    EMPTY_RESULTS = "EmptyResults"
    VECTOR_RESULTS = "VectorResults"


class DataType(enum.Enum):
    BYTE = "Byte"
    UINT16 = "UInt16"
    INT16 = "Int16"
    UINT32 = "UInt32"
    INT32 = "Int32"
    FLOAT32 = "Float32"
    FLOAT64 = "Float64"


class RasterType(enum.Enum):
    TILED_RASTER = "Tiled raster"
    ONE_FILE_RASTER = "One file raster"


class RasterFileType(enum.Enum):
    GEOTIFF = "GeoTiff"
    COG = "COG"


class EtagType(enum.Enum):
    AWS_MD5 = "AWS MD5 Etag"
    AWS_MULTIPART = "AWS Multipart Etag"
    GCS_CRC32C = "GCS CRC32C Etag"
    GCS_MD5 = "GCS MD5 Etag"


class VectorType(enum.Enum):
    ERROR_RECODE = "False positive/negative"


@marshmallow_dataclass.dataclass
class Etag:
    hash: str
    type: EtagType = dataclasses.field(metadata={"by_value": True})

    # TODO: Fix below as doesn't work on an s3 file uploaded with multipart
    @property
    def decoded_hash(self):
        return binascii.hexlify(base64.b64decode(self.md5_hash)).decode()


@marshmallow_dataclass.dataclass
class URI:
    class Meta:
        # Below is needed as URI used to include a type field, which is now deprecated
        unknown = EXCLUDE

    uri: typing.Union[Url, VSIPath, LocalPath, None]
    etag: typing.Optional[Etag] = None


@marshmallow_dataclass.dataclass
class Band:
    name: str
    metadata: dict
    no_data_value: typing.Union[int, float] = -32768
    activated: typing.Optional[bool] = dataclasses.field(default=True)
    add_to_map: typing.Optional[bool] = dataclasses.field(default=True)


@marshmallow_dataclass.dataclass
class TiledRaster:
    tile_uris: typing.List[URI]
    bands: typing.List[Band]
    datatype: DataType = dataclasses.field(metadata={"by_value": True})
    filetype: RasterFileType = dataclasses.field(metadata={"by_value": True})
    uri: typing.Optional[
        URI
    ] = None  # should point to a single VRT file linking the tiles
    extents: typing.Optional[
        typing.List[typing.Tuple[float, float, float, float]]
    ] = None
    type: RasterType = dataclasses.field(
        default=RasterType.TILED_RASTER,
        metadata={
            "by_value": True,
            "validate": validate.Equal(RasterType.TILED_RASTER),
        },
    )


@marshmallow_dataclass.dataclass
class Raster:
    uri: URI
    bands: typing.List[Band]
    datatype: DataType = dataclasses.field(metadata={"by_value": True})
    filetype: RasterFileType = dataclasses.field(metadata={"by_value": True})
    extent: typing.Optional[typing.Tuple[float, float, float, float]] = None
    type: RasterType = dataclasses.field(
        default=RasterType.ONE_FILE_RASTER,
        metadata={
            "by_value": True,
            "validate": validate.Equal(RasterType.ONE_FILE_RASTER),
        },
    )


@marshmallow_dataclass.dataclass
class RasterResults:
    name: str
    rasters: typing.Dict[str, typing.Union[Raster, TiledRaster]]
    uri: typing.Optional[
        URI
    ] = None  # should point to a single VRT or tif linking all rasters
    data: typing.Optional[dict] = dataclasses.field(default_factory=dict)
    type: ResultType = dataclasses.field(
        default=ResultType.RASTER_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.RASTER_RESULTS),
        },
    )

    def has_tiled_raster(self):
        for _, raster in self.rasters.items():
            if raster.type == RasterType.TILED_RASTER:
                return True

        return False

    def get_main_uris(self):
        return [raster.uri for raster in self.rasters.values()]

    def get_all_uris(self):
        if self.uri:
            uris = [self.uri]  # main vrt

        for raster in self.rasters.values():
            if raster.uri:
                uris.append(raster.uri)  # tif or main vrt (for TiledRaster)

            if raster.type == RasterType.TILED_RASTER:
                if raster.tile_uris:
                    uris.extend(raster.tile_uris)  # tif (for TiledRaster)

        return uris

    def get_bands(self):
        return [b for raster in self.rasters.values() for b in raster.bands]

    def get_extents(self):
        extents = []

        for raster in self.rasters.values():
            if raster.type == RasterType.ONE_FILE_RASTER:
                extents.append(raster.extent)
            elif raster.type == RasterType.TILED_RASTER:
                extents.extend(raster.extents)
        return [*set(extents)]

    def get_band_uris(self):
        return [raster.uri for raster in self.rasters.values() for _ in raster.bands]

    def update_uris(self, job_path):
        for uri in self.get_all_uris():
            possible_path = pathlib.Path(job_path.parent / uri.uri.name).resolve()
            if not uri.uri.exists() and possible_path.exists():
                uri.uri = possible_path

    def combine(self, other):
        "Merge with another RasterResults with matching bands"

        assert sorted(self.rasters.keys()) == sorted(other.rasters.keys())
        assert self.data == other.data
        for key in self.rasters:
            assert self.rasters[key].bands == other.rasters[key].bands
            assert self.rasters[key].datatype == other.rasters[key].datatype
            assert self.rasters[key].filetype == other.rasters[key].filetype

            tile_uris = []
            if self.rasters[key].type == RasterType.ONE_FILE_RASTER:
                tile_uris.append(self.rasters[key].uri)
            elif self.rasters[key].type == RasterType.TILED_RASTER:
                tile_uris.append(self.rasters[key].tile_uris)
            if other.rasters[key].type == RasterType.ONE_FILE_RASTER:
                tile_uris.append(other.rasters[key].uri)
            elif other.rasters[key].type == RasterType.TILED_RASTER:
                tile_uris.append(other.rasters[key].tile_uris)

            self.rasters[key] = TiledRaster(
                tile_uris=tile_uris,
                bands=self.rasters[key].bands,
                datatype=self.rasters[key].datatype,
                filetype=self.rasters[key].datatype,
            )


@marshmallow_dataclass.dataclass
class EmptyResults:
    class Meta:
        unknown = marshmallow.EXCLUDE

    name: typing.Optional[str] = None
    data_path: typing.Optional[typing.Union[VSIPath, LocalPath]] = None
    type: ResultType = dataclasses.field(
        default=ResultType.EMPTY_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.EMPTY_RESULTS),
        },
    )


@marshmallow_dataclass.dataclass
class CloudResults:
    class Meta:
        unknown = marshmallow.EXCLUDE

    name: str
    bands: typing.List[Band]
    urls: typing.List[Url]
    data_path: typing.Optional[typing.Union[VSIPath, LocalPath]] = dataclasses.field(
        default=None
    )
    other_paths: typing.Optional[
        typing.List[typing.Union[VSIPath, LocalPath]]
    ] = dataclasses.field(default_factory=list)
    data: typing.Optional[dict] = dataclasses.field(default_factory=dict)
    type: ResultType = dataclasses.field(
        default=ResultType.CLOUD_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.CLOUD_RESULTS),
        },
    )


@marshmallow_dataclass.dataclass
class FileResults:
    class Meta:
        unknown = marshmallow.EXCLUDE

    name: str
    uri: URI = dataclasses.field(default=None)
    other_uris: typing.List[URI] = dataclasses.field(default_factory=list)
    data: typing.Optional[dict] = dataclasses.field(default_factory=dict)

    type: ResultType = dataclasses.field(
        default=ResultType.FILE_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.FILE_RESULTS),
        },
    )

    def update_uris(self, job_path):
        for uri in [self.uri, *self.other_uris]:
            possible_path = pathlib.Path(job_path.parent / uri.uri.name).resolve()
            if not uri.uri.exists() and possible_path.exists():
                uri.uri = possible_path


@marshmallow_dataclass.dataclass
class JsonResults:
    class Meta:
        unknown = marshmallow.EXCLUDE

    name: str
    data: dict

    type: ResultType = dataclasses.field(
        default=ResultType.JSON_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.JSON_RESULTS),
        },
    )


@marshmallow_dataclass.dataclass
class TimeSeriesTableResult:
    class Meta:
        unknown = marshmallow.EXCLUDE

    name: str
    table: typing.List[dict]
    type: ResultType = dataclasses.field(
        default=ResultType.TIME_SERIES_TABLE,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.TIME_SERIES_TABLE),
        },
    )


@marshmallow_dataclass.dataclass
class VectorFalsePositive:
    uri: URI
    type: VectorType = dataclasses.field(
        default=VectorType.ERROR_RECODE,
        metadata={
            "by_value": True,
            "validate": validate.Equal(VectorType.ERROR_RECODE),
        },
    )


@marshmallow_dataclass.dataclass
class VectorResults:
    name: str
    vector: VectorFalsePositive
    extent: typing.Optional[typing.Tuple[float, float, float, float]] = None
    type: ResultType = dataclasses.field(
        default=ResultType.VECTOR_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.VECTOR_RESULTS),
        },
    )
    uri: typing.Optional[URI] = None

    def update_uris(self, job_path):
        for uri in [self.uri, self.vector.uri]:
            possible_path = pathlib.Path(job_path.parent / uri.uri.name).resolve()
            if possible_path.exists():
                uri.uri = possible_path
