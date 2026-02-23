"""Marshmallow compatibility regression tests for te_schemas.

These tests verify serialization/deserialization round-trips, enum handling,
custom fields, pre/post-load hooks, validators, and unknown-field exclusion
across all major te_schemas dataclasses.  They are designed to catch
regressions if the underlying marshmallow or marshmallow-dataclass versions
change (e.g. marshmallow 3→4 migration).
"""

import datetime
import pathlib
import uuid

import marshmallow
import marshmallow_dataclass
import pytest
from marshmallow.exceptions import ValidationError

from te_schemas import SchemaBase, validate_matrix
from te_schemas.algorithms import AlgorithmRunMode, ExecutionScript
from te_schemas.error_recode import (
    ErrorRecodeFeature,
    ErrorRecodePolygons,
    ErrorRecodeProperties,
)
from te_schemas.jobs import Job, JobStatus, RemoteScript, ResultsField, ScriptStatus
from te_schemas.land_cover import (
    LCClass,
    LCLegend,
    LCTransitionMeaningDeg,
)
from te_schemas.reporting import (
    Area,
    ErrorClassificationProperties,
    HotspotBrightspotProperties,
    Value,
    ValuesByYearDict,
)
from te_schemas.results import (
    URI,
    Band,
    CloudResults,
    DataType,
    EmptyResults,
    Etag,
    EtagType,
    FileResults,
    JsonResults,
    Raster,
    RasterFileType,
    RasterResults,
    RasterType,
    ResultType,
    TimeSeriesTableResult,
    TiledRaster,
    Vector,
    VectorFalsePositive,
    VectorResults,
    VectorType,
)
from te_schemas.schemas import (
    BandInfo,
    BandInfoSchema,
    CloudResultsSchema,
    TrendsEarthVersion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_band():
    return Band(name="test-band", metadata={"key": "val"})


def _make_uri(path="https://example.com/data.tif"):
    return URI(uri=path, etag=None)


def _make_raster():
    return Raster(
        uri=_make_uri(),
        bands=[_make_band()],
        datatype=DataType.INT16,
        filetype=RasterFileType.GEOTIFF,
    )


def _make_tiled_raster():
    return TiledRaster(
        tile_uris=[
            _make_uri("https://example.com/tile1.tif"),
            _make_uri("https://example.com/tile2.tif"),
        ],
        bands=[_make_band()],
        datatype=DataType.FLOAT32,
        filetype=RasterFileType.COG,
    )


def _make_raster_results():
    return RasterResults(
        name="Test raster results",
        rasters={"INT16": _make_raster()},
    )


def _make_vector_results():
    return VectorResults(
        name="Test vector",
        vector=Vector(
            uri=_make_uri("https://example.com/data.geojson"), type=VectorType.GENERIC
        ),
    )


def _make_job_dict(**overrides):
    base = {
        "id": str(uuid.uuid4()),
        "params": {},
        "progress": 100,
        "start_date": "2025-03-01T12:00:00",
        "status": "FINISHED",
        "end_date": "2025-03-01T13:00:00",
        "task_name": "Compat test job",
    }
    base.update(overrides)
    return base


# ===================================================================
# 1. Serialization round-trip tests
# ===================================================================


class TestRoundTrips:
    """Dump → load round-trips for all major dataclasses."""

    def test_band_roundtrip(self):
        obj = _make_band()
        data = Band.Schema().dump(obj)
        loaded = Band.Schema().load(data)
        assert loaded.name == obj.name
        assert loaded.metadata == obj.metadata
        assert loaded.no_data_value == obj.no_data_value

    def test_uri_roundtrip_url(self):
        obj = URI(uri="https://example.com/test.tif", etag=None)
        data = URI.Schema().dump(obj)
        loaded = URI.Schema().load(data)
        assert loaded.uri == obj.uri
        assert loaded.etag is None

    def test_uri_roundtrip_local_path(self):
        obj = URI(uri=pathlib.Path("/tmp/test.tif"), etag=None)
        data = URI.Schema().dump(obj)
        loaded = URI.Schema().load(data)
        # After round-trip through serialization the path becomes a string
        assert str(loaded.uri) == str(obj.uri)

    def test_uri_roundtrip_vsi_path(self):
        obj = URI(uri=pathlib.PurePosixPath("/vsis3/bucket/key.tif"), etag=None)
        data = URI.Schema().dump(obj)
        loaded = URI.Schema().load(data)
        assert str(loaded.uri) == "/vsis3/bucket/key.tif"

    def test_etag_roundtrip(self):
        obj = Etag(hash="abc123", type=EtagType.AWS_MD5)
        data = Etag.Schema().dump(obj)
        loaded = Etag.Schema().load(data)
        assert loaded.hash == "abc123"
        assert loaded.type == EtagType.AWS_MD5

    def test_raster_roundtrip(self):
        obj = _make_raster()
        data = Raster.Schema().dump(obj)
        loaded = Raster.Schema().load(data)
        assert loaded.datatype == DataType.INT16
        assert loaded.filetype == RasterFileType.GEOTIFF
        assert loaded.type == RasterType.ONE_FILE_RASTER
        assert len(loaded.bands) == 1

    def test_tiled_raster_roundtrip(self):
        obj = _make_tiled_raster()
        data = TiledRaster.Schema().dump(obj)
        loaded = TiledRaster.Schema().load(data)
        assert loaded.datatype == DataType.FLOAT32
        assert loaded.filetype == RasterFileType.COG
        assert loaded.type == RasterType.TILED_RASTER
        assert len(loaded.tile_uris) == 2

    def test_raster_results_roundtrip(self):
        obj = _make_raster_results()
        data = RasterResults.Schema().dump(obj)
        loaded = RasterResults.Schema().load(data)
        assert loaded.name == obj.name
        assert loaded.type == ResultType.RASTER_RESULTS
        assert "INT16" in loaded.rasters

    def test_vector_results_roundtrip(self):
        obj = _make_vector_results()
        data = VectorResults.Schema().dump(obj)
        loaded = VectorResults.Schema().load(data)
        assert loaded.name == obj.name
        assert loaded.type == ResultType.VECTOR_RESULTS
        assert loaded.vector.type == VectorType.GENERIC

    def test_vector_false_positive_roundtrip(self):
        vec = VectorFalsePositive(
            uri=_make_uri(),
            type=VectorType.ERROR_RECODE,
        )
        obj = VectorResults(name="FP test", vector=vec)
        data = VectorResults.Schema().dump(obj)
        loaded = VectorResults.Schema().load(data)
        assert loaded.vector.type == VectorType.ERROR_RECODE

    def test_empty_results_roundtrip(self):
        obj = EmptyResults(name="empty")
        data = EmptyResults.Schema().dump(obj)
        loaded = EmptyResults.Schema().load(data)
        assert loaded.name == "empty"
        assert loaded.type == ResultType.EMPTY_RESULTS

    def test_json_results_roundtrip(self):
        obj = JsonResults(name="json-test", data={"count": 42, "nested": {"a": 1}})
        data = JsonResults.Schema().dump(obj)
        loaded = JsonResults.Schema().load(data)
        assert loaded.data == {"count": 42, "nested": {"a": 1}}
        assert loaded.type == ResultType.JSON_RESULTS

    def test_file_results_roundtrip(self):
        obj = FileResults(name="file-test", uri=_make_uri())
        data = FileResults.Schema().dump(obj)
        loaded = FileResults.Schema().load(data)
        assert loaded.name == "file-test"
        assert loaded.type == ResultType.FILE_RESULTS

    def test_cloud_results_roundtrip(self):
        obj = CloudResults(
            name="cloud",
            bands=[_make_band()],
            urls=["https://example.com/file.tif"],
        )
        data = CloudResults.Schema().dump(obj)
        loaded = CloudResults.Schema().load(data)
        assert loaded.name == "cloud"
        assert loaded.type == ResultType.CLOUD_RESULTS

    def test_time_series_table_result_roundtrip(self):
        obj = TimeSeriesTableResult(
            name="ts-test",
            table=[{"time": [1, 2, 3], "y": [4, 5, 6]}],
        )
        data = TimeSeriesTableResult.Schema().dump(obj)
        loaded = TimeSeriesTableResult.Schema().load(data)
        assert loaded.name == "ts-test"
        assert loaded.type == ResultType.TIME_SERIES_TABLE

    def test_execution_script_roundtrip(self):
        obj = ExecutionScript(
            id=str(uuid.uuid4()),
            name="test-script",
            run_mode=AlgorithmRunMode.LOCAL,
        )
        data = ExecutionScript.Schema().dump(obj)
        loaded = ExecutionScript.Schema().load(data)
        assert loaded.name == "test-script"
        assert loaded.run_mode == AlgorithmRunMode.LOCAL

    def test_job_roundtrip(self):
        rr = _make_raster_results()
        job_data = _make_job_dict(
            results=RasterResults.Schema().dump(rr),
        )
        loaded = Job.Schema().load(job_data)
        assert isinstance(loaded, Job)
        dumped = Job.Schema().dump(loaded)
        reloaded = Job.Schema().load(dumped)
        assert reloaded.status == loaded.status
        assert reloaded.task_name == loaded.task_name

    def test_trends_earth_version_roundtrip(self):
        obj = TrendsEarthVersion(
            version="2.1.17",
            release_date=datetime.datetime(2025, 1, 15, 10, 30, 0),
            revision="abc123",
        )
        data = TrendsEarthVersion.Schema().dump(obj)
        loaded = TrendsEarthVersion.Schema().load(data)
        assert loaded.version == "2.1.17"
        assert loaded.revision == "abc123"

    def test_lc_class_roundtrip(self):
        obj = LCClass(
            code=1, name_short="Forest", name_long="Forest land", color="#00FF00"
        )
        data = LCClass.Schema().dump(obj)
        loaded = LCClass.Schema().load(data)
        assert loaded.code == 1
        assert loaded.name_short == "Forest"
        assert loaded.color == "#00FF00"

    def test_lc_legend_roundtrip(self):
        classes = [
            LCClass(code=1, name_short="Forest"),
            LCClass(code=2, name_short="Grass"),
        ]
        obj = LCLegend(name="Test legend", key=classes)
        data = LCLegend.Schema().dump(obj)
        loaded = LCLegend.Schema().load(data)
        assert loaded.name == "Test legend"
        assert len(loaded.key) == 2

    def test_error_recode_properties_roundtrip(self):
        obj = ErrorRecodeProperties(
            uuid=uuid.uuid4(),
            periods_affected=["baseline"],
            recode_deg_to=0,
            recode_stable_to=None,
            recode_imp_to=None,
        )
        data = ErrorRecodeProperties.Schema().dump(obj)
        loaded = ErrorRecodeProperties.Schema().load(data)
        assert loaded.periods_affected == ["baseline"]
        assert loaded.recode_deg_to == 0

    def test_error_recode_polygons_roundtrip(self):
        feature = ErrorRecodeFeature(
            type="Feature",
            geometry={
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
            },
            properties=ErrorRecodeProperties(
                uuid=uuid.uuid4(),
                periods_affected=["baseline", "report_1"],
            ),
        )
        obj = ErrorRecodePolygons(
            type="FeatureCollection",
            features=[feature],
            name="test",
            crs=None,
        )
        data = ErrorRecodePolygons.Schema().dump(obj)
        loaded = ErrorRecodePolygons.Schema().load(data)
        assert len(loaded.features) == 1
        assert loaded.features[0].properties.periods_affected == [
            "baseline",
            "report_1",
        ]

    def test_hotspot_properties_roundtrip(self):
        obj = HotspotBrightspotProperties(
            name="spot1",
            area=100.0,
            type="hotspot",
            process="deforestation",
            basis="field survey",
            periods=["baseline"],
        )
        data = HotspotBrightspotProperties.Schema().dump(obj)
        loaded = HotspotBrightspotProperties.Schema().load(data)
        assert loaded.type == "hotspot"
        assert loaded.area == 100.0

    def test_error_classification_properties_roundtrip(self):
        obj = ErrorClassificationProperties(
            area=50.0,
            type="false negative",
            place_name="Location A",
            process="misclass",
            basis="ground truth",
            periods="baseline",
        )
        data = ErrorClassificationProperties.Schema().dump(obj)
        loaded = ErrorClassificationProperties.Schema().load(data)
        assert loaded.type == "false negative"

    def test_value_roundtrip(self):
        obj = Value(name="metric", value=3.14)
        data = Value.Schema().dump(obj)
        loaded = Value.Schema().load(data)
        assert loaded.value == pytest.approx(3.14)

    def test_area_roundtrip(self):
        obj = Area(name="test-area", area=1234.56)
        data = Area.Schema().dump(obj)
        loaded = Area.Schema().load(data)
        assert loaded.area == pytest.approx(1234.56)

    def test_values_by_year_dict_roundtrip(self):
        obj = ValuesByYearDict(
            name="soc",
            unit="tonnes/ha",
            values={2020: {"forest": 10.0, "grass": 5.0}},
        )
        data = ValuesByYearDict.Schema().dump(obj)
        loaded = ValuesByYearDict.Schema().load(data)
        assert loaded.name == "soc"


# ===================================================================
# 2. Enum by_value serialization tests
# ===================================================================


class TestEnumByValue:
    """Ensure enums are serialized using their *value*, not their name."""

    def test_algorithm_run_mode_by_value(self):
        obj = ExecutionScript(id="test", name="s", run_mode=AlgorithmRunMode.LOCAL)
        data = ExecutionScript.Schema().dump(obj)
        assert data["run_mode"] == "local"

    def test_algorithm_run_mode_not_applicable(self):
        obj = ExecutionScript(id="test", name="s")
        data = ExecutionScript.Schema().dump(obj)
        assert data["run_mode"] == 0  # NOT_APPLICABLE value is int 0

    def test_script_status_by_value(self):
        data = {
            "id": str(uuid.uuid4()),
            "name": "s",
            "slug": "s",
            "description": "d",
            "status": "SUCCESS",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "user_id": str(uuid.uuid4()),
            "public": True,
            "cpu_reservation": None,
            "cpu_limit": None,
            "memory_reservation": None,
            "memory_limit": None,
        }
        loaded = RemoteScript.Schema().load(data)
        assert loaded.status == ScriptStatus.SUCCESS
        dumped = RemoteScript.Schema().dump(loaded)
        assert dumped["status"] == "SUCCESS"

    def test_job_status_by_value(self):
        job_data = _make_job_dict()
        loaded = Job.Schema().load(job_data)
        assert loaded.status == JobStatus.FINISHED
        dumped = Job.Schema().dump(loaded)
        assert dumped["status"] == "FINISHED"

    def test_data_type_by_value(self):
        raster = _make_raster()
        data = Raster.Schema().dump(raster)
        assert data["datatype"] == "Int16"

    def test_raster_file_type_by_value(self):
        raster = _make_raster()
        data = Raster.Schema().dump(raster)
        assert data["filetype"] == "GeoTiff"

    def test_raster_type_by_value(self):
        raster = _make_raster()
        data = Raster.Schema().dump(raster)
        assert data["type"] == "One file raster"

    def test_result_type_by_value(self):
        rr = _make_raster_results()
        data = RasterResults.Schema().dump(rr)
        assert data["type"] == "RasterResults"

    def test_vector_type_by_value(self):
        vr = _make_vector_results()
        data = VectorResults.Schema().dump(vr)
        assert data["vector"]["type"] == "Generic"

    def test_etag_type_by_value(self):
        obj = Etag(hash="abc", type=EtagType.GCS_CRC32C)
        data = Etag.Schema().dump(obj)
        assert data["type"] == "GCS CRC32C Etag"

    def test_all_result_type_values(self):
        """Verify each ResultType enum member can round-trip via its value."""
        for rt in ResultType:
            raw = rt.value
            assert ResultType(raw) is rt

    def test_all_data_type_values(self):
        for dt in DataType:
            raw = dt.value
            assert DataType(raw) is dt


# ===================================================================
# 3. Custom field tests
# ===================================================================


class TestCustomFields:
    """VSIPathField, LocalPathField, ResultsField."""

    def test_vsi_path_field_roundtrip(self):
        from te_schemas.results import VSIPathField

        f = VSIPathField()
        path = pathlib.PurePosixPath("/vsis3/bucket/key.tif")
        serialized = f._serialize(path, None, None)
        assert serialized == "/vsis3/bucket/key.tif"
        deserialized = f._deserialize(serialized, None, None)
        assert deserialized == path

    def test_vsi_path_field_none(self):
        from te_schemas.results import VSIPathField

        f = VSIPathField()
        assert f._serialize(None, None, None) == ""

    def test_local_path_field_roundtrip(self):
        from te_schemas.results import LocalPathField

        f = LocalPathField()
        path = pathlib.Path("/tmp/data.tif")
        serialized = f._serialize(path, None, None)
        assert serialized == str(path)
        deserialized = f._deserialize(serialized, None, None)
        assert deserialized == path

    def test_local_path_field_none(self):
        from te_schemas.results import LocalPathField

        f = LocalPathField()
        assert f._serialize(None, None, None) == ""

    def test_results_field_single_raster(self):
        rf = ResultsField()
        rr = _make_raster_results()
        dumped = RasterResults.Schema().dump(rr)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, RasterResults)

    def test_results_field_single_json(self):
        rf = ResultsField()
        jr = JsonResults(name="j", data={"k": "v"})
        dumped = JsonResults.Schema().dump(jr)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, JsonResults)

    def test_results_field_single_vector(self):
        rf = ResultsField()
        vr = _make_vector_results()
        dumped = VectorResults.Schema().dump(vr)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, VectorResults)

    def test_results_field_single_empty(self):
        rf = ResultsField()
        er = EmptyResults(name="e")
        dumped = EmptyResults.Schema().dump(er)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, EmptyResults)

    def test_results_field_single_file(self):
        rf = ResultsField()
        fr = FileResults(name="f", uri=_make_uri())
        dumped = FileResults.Schema().dump(fr)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, FileResults)

    def test_results_field_single_timeseries(self):
        rf = ResultsField()
        ts = TimeSeriesTableResult(name="ts", table=[{"time": [1], "y": [2]}])
        dumped = TimeSeriesTableResult.Schema().dump(ts)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, TimeSeriesTableResult)

    def test_results_field_single_cloud(self):
        rf = ResultsField()
        cr = CloudResults(
            name="c", bands=[_make_band()], urls=["https://example.com/f.tif"]
        )
        dumped = CloudResults.Schema().dump(cr)
        loaded = rf._deserialize(dumped, None, None)
        assert isinstance(loaded, CloudResults)

    def test_results_field_list(self):
        rf = ResultsField()
        rr = _make_raster_results()
        jr = JsonResults(name="j", data={})
        items = [RasterResults.Schema().dump(rr), JsonResults.Schema().dump(jr)]
        loaded = rf._deserialize(items, None, None)
        assert isinstance(loaded, list)
        assert len(loaded) == 2
        assert isinstance(loaded[0], RasterResults)
        assert isinstance(loaded[1], JsonResults)

    def test_results_field_none(self):
        rf = ResultsField()
        assert rf._deserialize(None, None, None) is None

    def test_results_field_serialize_single(self):
        rf = ResultsField()
        rr = _make_raster_results()
        serialized = rf._serialize(rr, None, None)
        assert isinstance(serialized, dict)
        assert serialized["type"] == "RasterResults"

    def test_results_field_serialize_list(self):
        rf = ResultsField()
        rr = _make_raster_results()
        jr = JsonResults(name="j", data={})
        serialized = rf._serialize([rr, jr], None, None)
        assert isinstance(serialized, list)
        assert len(serialized) == 2

    def test_results_field_serialize_none(self):
        rf = ResultsField()
        assert rf._serialize(None, None, None) is None


# ===================================================================
# 4. Pre/post-load hook tests
# ===================================================================


class TestHooks:
    def test_job_pre_load_sets_script_from_params(self):
        """@pre_load properly extracts script from params."""
        job_data = _make_job_dict(
            params={"script": {"id": "my-id", "name": "My Script"}},
        )
        loaded = Job.Schema().load(job_data)
        assert loaded.script is not None
        assert loaded.script.name == "My Script"

    def test_job_pre_load_falls_back_script_id(self):
        """@pre_load creates script from script_id when no script in params."""
        job_data = _make_job_dict(
            script_id="fallback-id",
            params={},
        )
        loaded = Job.Schema().load(job_data)
        assert loaded.script is not None

    def test_job_pre_load_parses_script_name_version(self):
        """@pre_load extracts version from script name like 'Land Cover 1_0_3'."""
        job_data = _make_job_dict(
            params={"script": {"id": "lc-id", "name": "Land Cover 1_0_3"}},
        )
        loaded = Job.Schema().load(job_data)
        assert loaded.script.name == "Land Cover"
        assert loaded.script.version == "1.0.3"

    def test_job_pre_load_extracts_task_name(self):
        """@pre_load moves task_name from params to top level."""
        job_data = _make_job_dict(
            params={"task_name": "My Task"},
        )
        loaded = Job.Schema().load(job_data)
        assert loaded.task_name == "My Task"

    def test_job_post_load_sets_utc_timezone(self):
        """@post_load adds UTC timezone to start_date and end_date."""
        job_data = _make_job_dict()
        loaded = Job.Schema().load(job_data)
        assert loaded.start_date.tzinfo == datetime.timezone.utc
        if loaded.end_date:
            assert loaded.end_date.tzinfo == datetime.timezone.utc

    def test_execution_script_pre_load_sets_slug(self):
        """@pre_load generates slug from name if not provided."""
        data = {"id": "test-id", "name": "My Script"}
        loaded = ExecutionScript.Schema().load(data)
        assert loaded.slug is not None
        assert loaded.slug != ""

    def test_remote_script_post_load_sets_timezone(self):
        data = {
            "id": str(uuid.uuid4()),
            "name": "s",
            "slug": "s",
            "description": "d",
            "status": "SUCCESS",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-06-15T12:00:00",
            "user_id": str(uuid.uuid4()),
            "public": True,
            "cpu_reservation": None,
            "cpu_limit": None,
            "memory_reservation": None,
            "memory_limit": None,
        }
        loaded = RemoteScript.Schema().load(data)
        assert loaded.created_at.tzinfo == datetime.timezone.utc
        assert loaded.updated_at.tzinfo == datetime.timezone.utc


# ===================================================================
# 5. Validation tests
# ===================================================================


class TestValidation:
    def test_path_validator_accepts_vsis3(self):
        from te_schemas.results import PathValidator

        v = PathValidator(r"/vsi(s3)|(gs)")
        result = v("/vsis3/bucket/path")
        assert result == "/vsis3/bucket/path"

    def test_path_validator_accepts_vsigs(self):
        from te_schemas.results import PathValidator

        v = PathValidator(r"/vsi(s3)|(gs)")
        result = v("/vsigs/bucket/path")
        assert result == "/vsigs/bucket/path"

    def test_path_validator_rejects_invalid(self):
        from te_schemas.results import PathValidator

        v = PathValidator(r"/vsi(s3)|(gs)")
        with pytest.raises(ValidationError):
            v("/invalid/path")

    def test_lc_class_color_validation_valid(self):
        data = {"code": 1, "color": "#FF0000"}
        loaded = LCClass.Schema().load(data)
        assert loaded.color == "#FF0000"

    def test_lc_class_color_validation_invalid(self):
        with pytest.raises(ValidationError):
            LCClass.Schema().load({"code": 1, "color": "not-a-color"})

    def test_lc_class_name_short_max_length(self):
        with pytest.raises(ValidationError):
            LCClass.Schema().load({"code": 1, "name_short": "a" * 21})

    def test_lc_class_name_long_max_length(self):
        with pytest.raises(ValidationError):
            LCClass.Schema().load({"code": 1, "name_long": "a" * 121})

    def test_error_recode_deg_to_validation(self):
        """recode_deg_to only accepts None, -32768, 0, 1."""
        obj = ErrorRecodeProperties(
            uuid=uuid.uuid4(),
            periods_affected=["baseline"],
            recode_deg_to=0,
        )
        data = ErrorRecodeProperties.Schema().dump(obj)
        loaded = ErrorRecodeProperties.Schema().load(data)
        assert loaded.recode_deg_to == 0

    def test_error_recode_deg_to_rejects_invalid(self):
        data = {
            "uuid": str(uuid.uuid4()),
            "periods_affected": ["baseline"],
            "recode_deg_to": 99,
        }
        with pytest.raises(ValidationError):
            ErrorRecodeProperties.Schema().load(data)

    def test_error_recode_feature_type_validation(self):
        """type must be 'Feature'."""
        data = {
            "type": "NOT_FEATURE",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {
                "uuid": str(uuid.uuid4()),
                "periods_affected": ["baseline"],
            },
        }
        with pytest.raises(ValidationError):
            ErrorRecodeFeature.Schema().load(data)

    def test_error_recode_polygons_type_validation(self):
        """type must be 'FeatureCollection'."""
        data = {
            "type": "NOT_FC",
            "features": [],
            "name": "t",
            "crs": None,
        }
        with pytest.raises(ValidationError):
            ErrorRecodePolygons.Schema().load(data)

    def test_hotspot_type_validation(self):
        with pytest.raises(ValidationError):
            HotspotBrightspotProperties.Schema().load(
                {
                    "name": "h",
                    "area": 1.0,
                    "type": "neither",
                    "process": "p",
                    "basis": "b",
                    "periods": ["baseline"],
                }
            )

    def test_error_classification_type_validation(self):
        with pytest.raises(ValidationError):
            ErrorClassificationProperties.Schema().load(
                {
                    "area": 1.0,
                    "type": "invalid",
                    "place_name": "p",
                    "process": "p",
                    "basis": "b",
                    "periods": "baseline",
                }
            )

    def test_area_negative_validation(self):
        with pytest.raises(ValidationError):
            Area.Schema().load({"name": "a", "area": -1.0})

    def test_transition_meaning_deg_validation(self):
        """LCTransitionMeaningDeg meaning must be degradation/stable/improvement."""
        c1 = LCClass(code=1, name_short="A")
        c2 = LCClass(code=2, name_short="B")
        obj = LCTransitionMeaningDeg(initial=c1, final=c2, meaning="degradation")
        data = LCTransitionMeaningDeg.Schema().dump(obj)
        loaded = LCTransitionMeaningDeg.Schema().load(data)
        assert loaded.meaning == "degradation"

    def test_transition_meaning_deg_invalid(self):
        c1 = LCClass(code=1, name_short="A")
        c2 = LCClass(code=2, name_short="B")
        data = LCTransitionMeaningDeg.Schema().dump(
            LCTransitionMeaningDeg(initial=c1, final=c2, meaning="degradation")
        )
        data["meaning"] = "invalid_meaning"
        with pytest.raises(ValidationError):
            LCTransitionMeaningDeg.Schema().load(data)

    def test_validate_matrix_happy_path(self):
        classes = [LCClass(code=1, name_short="A"), LCClass(code=2, name_short="B")]
        legend = LCLegend(name="test", key=classes)
        transitions = [
            {"initial": classes[0], "final": classes[0]},
            {"initial": classes[0], "final": classes[1]},
            {"initial": classes[1], "final": classes[0]},
            {"initial": classes[1], "final": classes[1]},
        ]
        # Should not raise
        validate_matrix(legend, transitions)

    def test_validate_matrix_missing_transition(self):
        classes = [LCClass(code=1, name_short="A"), LCClass(code=2, name_short="B")]
        legend = LCLegend(name="test", key=classes)
        transitions = [
            {"initial": classes[0], "final": classes[0]},
        ]
        with pytest.raises(ValidationError):
            validate_matrix(legend, transitions)

    def test_raster_type_validation_on_raster(self):
        """Raster.type must be ONE_FILE_RASTER."""
        raster = _make_raster()
        data = Raster.Schema().dump(raster)
        data["type"] = "Tiled raster"  # wrong type for Raster
        with pytest.raises(ValidationError):
            Raster.Schema().load(data)

    def test_result_type_validation_on_raster_results(self):
        """RasterResults.type must be 'RasterResults'."""
        rr = _make_raster_results()
        data = RasterResults.Schema().dump(rr)
        data["type"] = "JsonResults"
        with pytest.raises(ValidationError):
            RasterResults.Schema().load(data)


# ===================================================================
# 6. Unknown field handling (EXCLUDE) tests
# ===================================================================


class TestUnknownFieldExclusion:
    """Classes with Meta: unknown = EXCLUDE should silently drop extra fields."""

    def test_execution_script_excludes_unknown(self):
        data = {"id": "test-id", "name": "s", "unknown_field": "dropped"}
        loaded = ExecutionScript.Schema().load(data)
        assert not hasattr(loaded, "unknown_field")

    def test_uri_excludes_unknown(self):
        data = {"uri": "https://example.com/test.tif", "unknown_legacy": "dropped"}
        loaded = URI.Schema().load(data)
        assert not hasattr(loaded, "unknown_legacy")

    def test_empty_results_excludes_unknown(self):
        data = {"name": "e", "type": "EmptyResults", "extra": True}
        loaded = EmptyResults.Schema().load(data)
        assert not hasattr(loaded, "extra")

    def test_json_results_excludes_unknown(self):
        data = {"name": "j", "data": {}, "type": "JsonResults", "extra": 42}
        loaded = JsonResults.Schema().load(data)
        assert not hasattr(loaded, "extra")

    def test_vector_results_excludes_unknown(self):
        data = {
            "name": "v",
            "vector": {"uri": None, "type": "Generic"},
            "type": "VectorResults",
            "old_vector_type": "legacy",
        }
        loaded = VectorResults.Schema().load(data)
        assert not hasattr(loaded, "old_vector_type")

    def test_error_recode_properties_excludes_unknown(self):
        data = {
            "uuid": str(uuid.uuid4()),
            "periods_affected": ["baseline"],
            "bonus_field": "nope",
        }
        loaded = ErrorRecodeProperties.Schema().load(data)
        assert not hasattr(loaded, "bonus_field")


# ===================================================================
# 7. SchemaBase functionality tests
# ===================================================================


class TestSchemaBase:
    """Tests for the SchemaBase helper methods."""

    def test_schema_method_returns_schema(self):
        klass = ExecutionScript
        schema = klass.schema()
        assert hasattr(schema, "load")
        assert hasattr(schema, "dump")

    def test_validate_method(self):
        obj = ExecutionScript(id="test", name="s")
        # Should not raise
        obj.validate()

    def test_dump_method(self):
        obj = ExecutionScript(id="test", name="s")
        data = obj.dump()
        assert isinstance(data, dict)
        assert "name" in data

    def test_dumps_method(self):
        obj = ExecutionScript(id="test", name="s")
        json_str = obj.dumps()
        assert isinstance(json_str, str)
        assert "test" in json_str

    def test_schema_factory_is_callable(self):
        """Schema attribute must be callable (returns schema instance)."""
        schema = ExecutionScript.Schema()
        assert isinstance(schema, marshmallow.Schema)

    def test_normalize_recovers_broken_schema(self):
        """_normalize_schema_attribute fixes a broken Schema attribute."""

        @marshmallow_dataclass.dataclass
        class TempClass(SchemaBase):
            value: int

        TempClass.Schema = "broken"
        TempClass._normalize_schema_attribute()
        schema = TempClass.Schema()
        loaded = schema.load({"value": 7})
        assert loaded.value == 7

    def test_lc_class_is_schema_base(self):
        """LCClass inherits SchemaBase, so schema/validate/dump should work."""
        obj = LCClass(code=1, name_short="Forest")
        data = obj.dump()
        assert data["code"] == 1

    def test_lc_legend_is_schema_base(self):
        obj = LCLegend(name="test", key=[LCClass(code=1)])
        data = obj.dump()
        assert data["name"] == "test"


# ===================================================================
# 8. Legacy schema tests (schemas.py manual Schema classes)
# ===================================================================


class TestLegacySchemas:
    def test_band_info_schema_dump_defaults(self):
        """BandInfoSchema uses dump_default for add_to_map and activated."""
        schema = BandInfoSchema()
        data = schema.dump(BandInfo(name="b", metadata={"k": "v"}))
        assert data["add_to_map"] is True
        assert data["activated"] is True

    def test_cloud_results_schema_post_load(self):
        """CloudResultsSchema @post_load pops 'type' and returns object."""
        schema = CloudResultsSchema()
        data = {
            "type": "CloudResults",
            "name": "test",
            "bands": [
                {
                    "name": "b",
                    "no_data_value": -32768,
                    "add_to_map": True,
                    "activated": True,
                    "metadata": {},
                }
            ],
            "urls": [],
        }
        loaded = schema.load(data)
        from te_schemas.schemas import CloudResults as LegacyCloudResults

        assert isinstance(loaded, LegacyCloudResults)


# ===================================================================
# 9. Metadata passthrough tests (critical for marshmallow 4 compat)
# ===================================================================


class TestMetadataPassthrough:
    """Verify that metadata keys used in dataclasses.field(metadata={...})
    are correctly handled by marshmallow-dataclass.  This is the most
    critical area for marshmallow 4 migration."""

    def test_by_value_metadata_loads(self):
        """Fields with metadata={'by_value': True} must deserialize enum from value."""
        data = {"id": "t", "name": "s", "run_mode": "local"}
        loaded = ExecutionScript.Schema().load(data)
        assert loaded.run_mode == AlgorithmRunMode.LOCAL

    def test_by_value_metadata_dumps(self):
        """Fields with metadata={'by_value': True} must serialize enum as value."""
        obj = ExecutionScript(id="t", name="s", run_mode=AlgorithmRunMode.BOTH)
        data = ExecutionScript.Schema().dump(obj)
        assert data["run_mode"] == "both"

    def test_validate_metadata_passes_validator(self):
        """Fields with metadata={'validate': ...} must apply the validator."""
        data = {"code": 1, "color": "#AABBCC"}
        loaded = LCClass.Schema().load(data)
        assert loaded.color == "#AABBCC"

    def test_validate_metadata_rejects_invalid(self):
        data = {"code": 1, "color": "invalid"}
        with pytest.raises(ValidationError):
            LCClass.Schema().load(data)

    def test_marshmallow_field_metadata_works(self):
        """metadata={'marshmallow_field': ResultsField(...)} must use custom field."""
        rr = _make_raster_results()
        job_data = _make_job_dict(results=RasterResults.Schema().dump(rr))
        loaded = Job.Schema().load(job_data)
        assert isinstance(loaded.results, RasterResults)

    def test_combined_by_value_and_validate_metadata(self):
        """Fields with both by_value and validate in metadata must work."""
        rr = _make_raster_results()
        data = RasterResults.Schema().dump(rr)
        # type field has both by_value=True and validate=Equal(...)
        assert data["type"] == "RasterResults"
        loaded = RasterResults.Schema().load(data)
        assert loaded.type == ResultType.RASTER_RESULTS


# ===================================================================
# 10. Job with various result types integration tests
# ===================================================================


class TestJobIntegration:
    def test_job_with_null_results(self):
        job_data = _make_job_dict(results=None)
        loaded = Job.Schema().load(job_data)
        assert loaded.results is None

    def test_job_with_raster_results(self):
        rr = _make_raster_results()
        job_data = _make_job_dict(results=RasterResults.Schema().dump(rr))
        loaded = Job.Schema().load(job_data)
        assert loaded.is_raster()

    def test_job_with_vector_results(self):
        vr = _make_vector_results()
        job_data = _make_job_dict(results=VectorResults.Schema().dump(vr))
        loaded = Job.Schema().load(job_data)
        assert loaded.is_vector()

    def test_job_with_mixed_list_results(self):
        rr = _make_raster_results()
        jr = JsonResults(name="j", data={"k": "v"})
        job_data = _make_job_dict(
            results=[
                RasterResults.Schema().dump(rr),
                JsonResults.Schema().dump(jr),
            ]
        )
        loaded = Job.Schema().load(job_data)
        assert isinstance(loaded.results, list)
        assert len(loaded.results) == 2
        assert loaded.is_raster()

    def test_job_with_empty_list_results(self):
        job_data = _make_job_dict(results=[])
        loaded = Job.Schema().load(job_data)
        assert loaded.results == []

    def test_job_full_dump_load_cycle(self):
        """Full cycle: create Job data → load → dump → reload."""
        rr = _make_raster_results()
        job_data = _make_job_dict(
            results=RasterResults.Schema().dump(rr),
            params={"task_name": "Full cycle test"},
        )
        loaded1 = Job.Schema().load(job_data)
        dumped = Job.Schema().dump(loaded1)
        loaded2 = Job.Schema().load(dumped)
        assert loaded2.task_name == "Full cycle test"
        assert loaded2.status == JobStatus.FINISHED
        assert isinstance(loaded2.results, RasterResults)
