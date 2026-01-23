"""
Result schemas for Trends.Earth analysis outputs.

This module defines the data structures for representing analysis results,
including raster outputs, JSON data, and file references. These schemas
are used for serialization/deserialization when communicating with the
Trends.Earth API and for storing job results.

Classes:
    Band: Metadata for a single raster band.
    Raster: A single-file raster layer.
    TiledRaster: A multi-file tiled raster layer.
    RasterResults: Results containing raster layers (primary result type).
    JsonResults: Results containing only JSON data.
    FileResults: Results referencing file outputs.
    CloudResults: Results from cloud processing.
    URI: Universal resource identifier for file locations.
    Etag: File hash for integrity verification.

Enums:
    DataType: Pixel data types (Int16, Float32, etc.).
    RasterType: Single file vs tiled raster.
    RasterFileType: GeoTiff or COG format.
    ResultType: Type discriminator for result classes.
"""

from __future__ import annotations

import base64
import binascii
import dataclasses
import enum
import pathlib
import typing

import marshmallow
import marshmallow_dataclass
from marshmallow import EXCLUDE, fields, validate
from marshmallow.exceptions import ValidationError
from marshmallow_dataclass.typing import Url


class PathValidator(validate.Regexp):
    def __call__(self, value):
        if self.regex.match(str(value)) is None:
            raise ValidationError(self._format_error(value))

        return value


class VSIPathField(fields.Field):
    def _serialize(
        self, value: typing.Union[None, pathlib.PurePosixPath], attr, obj, **kwargs
    ):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value: str, attr, data, **kwargs):
        return pathlib.PurePosixPath(value)


VSIPath = typing.Annotated[
    pathlib.PurePosixPath, VSIPathField(validate=PathValidator(r"/vsi(s3)|(gs)"))
]


class LocalPathField(fields.Field):
    def _serialize(self, value: pathlib.Path, attr, obj, **kwargs):
        if value is None:
            return ""

        return str(value)

    def _deserialize(self, value: dict, attr, data, **kwargs):
        return pathlib.Path(value)


LocalPath = typing.Annotated[pathlib.Path, LocalPathField]


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
    GENERIC = "Generic"


@marshmallow_dataclass.dataclass
class Etag:
    hash: str
    type: EtagType = dataclasses.field(metadata={"by_value": True})

    # TODO: Fix below as doesn't work on an s3 file uploaded with multipart
    @property
    def decoded_hash(self):
        return binascii.hexlify(base64.b64decode(self.hash)).decode()


@marshmallow_dataclass.dataclass
class URI:
    class Meta:
        # Below is needed as URI used to include a type field, which is now deprecated
        unknown = EXCLUDE

    uri: typing.Union[Url, VSIPath, LocalPath, None]
    etag: typing.Optional[Etag] = None


@marshmallow_dataclass.dataclass
class Band:
    """
    Metadata for a single band in a raster file.

    Attributes:
        name: Human-readable band name (e.g., "SDG 15.3.1 Indicator - Baseline").
        metadata: Dictionary of additional band metadata.
        no_data_value: Value representing no data (default: -32768).
        activated: Whether the band should be processed (default: True).
        add_to_map: Whether the band should be displayed in the map (default: True).
    """

    name: str
    metadata: dict
    no_data_value: typing.Union[int, float] = -32768
    activated: typing.Optional[bool] = dataclasses.field(default=True)
    add_to_map: typing.Optional[bool] = dataclasses.field(default=True)


@marshmallow_dataclass.dataclass
class TiledRaster:
    """
    A tiled raster composed of multiple files.

    Used for large rasters that are split across multiple GeoTIFF tiles,
    typically with a VRT file linking them together.

    Attributes:
        tile_uris: List of URIs pointing to individual tile files.
        bands: List of Band metadata for the raster.
        datatype: Pixel data type (e.g., Int16, Float32).
        filetype: File format (GeoTiff or COG).
        uri: Optional URI to a VRT file linking all tiles.
        extents: Optional list of (minx, miny, maxx, maxy) bounding boxes.
        type: Must be RasterType.TILED_RASTER.
    """

    tile_uris: typing.List[URI]
    bands: typing.List[Band]
    datatype: DataType = dataclasses.field(metadata={"by_value": True})
    filetype: RasterFileType = dataclasses.field(metadata={"by_value": True})
    uri: typing.Optional[URI] = (
        None  # should point to a single VRT file linking the tiles
    )
    extents: typing.Optional[typing.List[typing.Tuple[float, float, float, float]]] = (
        dataclasses.field(default_factory=list)
    )
    type: RasterType = dataclasses.field(
        default=RasterType.TILED_RASTER,
        metadata={
            "by_value": True,
            "validate": validate.Equal(RasterType.TILED_RASTER),
        },
    )


@marshmallow_dataclass.dataclass
class Raster:
    """
    A single-file raster layer.

    Represents a GeoTIFF or COG file containing one or more bands.

    Attributes:
        uri: URI pointing to the raster file (S3, GCS, or local path).
        bands: List of Band metadata for each band in the file.
        datatype: Pixel data type (e.g., Int16, Float32).
        filetype: File format (GeoTiff or COG).
        extent: Optional bounding box as (minx, miny, maxx, maxy).
        type: Must be RasterType.ONE_FILE_RASTER.
    """

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
    """
    Results containing one or more raster layers.

    The primary result type for land degradation analysis jobs. Contains
    raster data organized by data type (e.g., Int16, Float32) along with
    optional metadata and summary statistics.

    Attributes:
        name: Human-readable result name (e.g., "SDG 15.3.1 Indicator").
        rasters: Dict mapping data type keys to Raster or TiledRaster objects.
        uri: Optional URI to a combined VRT or TIF linking all rasters.
        data: Optional dict containing additional result data (e.g., summaries).
        type: Must be ResultType.RASTER_RESULTS.

    Example:
        Typical structure after serialization::

            {
                "name": "SDG 15.3.1 Indicator",
                "type": "RasterResults",
                "rasters": {
                    "Int16": {
                        "uri": {...},
                        "bands": [...],
                        "datatype": "Int16",
                        "filetype": "GeoTiff",
                        "type": "One file raster"
                    }
                },
                "data": {"report": {"summary": {...}}}
            }
    """

    name: str
    rasters: typing.Dict[str, typing.Union[Raster, TiledRaster]]
    uri: typing.Optional[URI] = (
        None  # should point to a single VRT or tif linking all rasters
    )
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
        else:
            uris = []

        for raster in self.rasters.values():
            if raster.uri:
                uris.append(raster.uri)  # tif or main vrt (for TiledRaster)

            if raster.type == RasterType.TILED_RASTER:
                if raster.tile_uris:  # type: ignore
                    uris.extend(
                        raster.tile_uris  # type: ignore
                    )  # tif (for TiledRaster)

        return uris

    def get_bands(self):
        return [b for raster in self.rasters.values() for b in raster.bands]

    def get_extents(self):
        extents: typing.List[typing.Tuple[float, float, float, float]] = []

        for raster in self.rasters.values():
            if raster.type == RasterType.ONE_FILE_RASTER:
                extents.append(raster.extent)  # type: ignore
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
                tile_uris.extend(self.rasters[key].tile_uris)  # type: ignore
            if other.rasters[key].type == RasterType.ONE_FILE_RASTER:
                tile_uris.append(other.rasters[key].uri)
            elif other.rasters[key].type == RasterType.TILED_RASTER:
                tile_uris.extend(other.rasters[key].tile_uris)

            self.rasters[key] = TiledRaster(
                tile_uris=tile_uris,
                bands=self.rasters[key].bands,
                datatype=self.rasters[key].datatype,
                filetype=self.rasters[key].filetype,
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
    other_paths: typing.Optional[typing.List[typing.Union[VSIPath, LocalPath]]] = (
        dataclasses.field(default_factory=list)
    )
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

    def get_all_uris(self):
        """Return a list of all URI objects associated with this file result.

        Mirrors the interface provided by RasterResults so that downstream
        code can treat different result types uniformly.
        The primary archive or file (self.uri) is returned first (if set),
        followed by any auxiliary URIs in other_uris.
        """
        uris = []
        if self.uri is not None:
            uris.append(self.uri)
        uris.extend(self.other_uris)
        return uris


@marshmallow_dataclass.dataclass
class JsonResults:
    """
    Results containing only JSON data without raster outputs.

    Used for analysis jobs that produce statistics or reports without
    generating new raster files (e.g., sdg-15-3-1-stats script).

    Attributes:
        name: Human-readable result name.
        data: Dictionary containing all result data (statistics, reports, etc.).
        type: Must be ResultType.JSON_RESULTS.
    """

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
    """
    Generic vector results class for any vector/geojson output.

    For generic vector results, only `name` and `uri` are required.
    The `vector` field is optional and used for specific vector types
    like ErrorRecode that need additional metadata.
    """

    name: str
    uri: typing.Optional[URI] = None
    extent: typing.Optional[typing.Tuple[float, float, float, float]] = None
    vector: typing.Optional[VectorFalsePositive] = None
    vector_type: VectorType = dataclasses.field(
        default=VectorType.GENERIC,
        metadata={"by_value": True},
    )
    type: ResultType = dataclasses.field(
        default=ResultType.VECTOR_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.VECTOR_RESULTS),
        },
    )

    def update_uris(self, job_path):
        uris_to_update = [self.uri]
        if self.vector is not None and self.vector.uri is not None:
            uris_to_update.append(self.vector.uri)

        for uri in uris_to_update:
            if uri is not None and uri.uri is not None:
                possible_path = pathlib.Path(job_path.parent / uri.uri.name).resolve()
                if possible_path.exists():
                    uri.uri = possible_path
