"""Tests for jobs.py schema and result handling."""

import uuid
from pathlib import Path

import pytest

from te_schemas.jobs import Job, ResultsField
from te_schemas.results import (
    URI,
    Band,
    DataType,
    EmptyResults,
    FileResults,
    JsonResults,
    Raster,
    RasterFileType,
    RasterResults,
    Vector,
    VectorFalsePositive,
    VectorResults,
    VectorType,
)


# =============================================================================
# Fixtures for common test data
# =============================================================================


@pytest.fixture
def base_job_data():
    """Base job data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "params": {},
        "progress": 100,
        "start_date": "2024-01-15T10:30:00",
        "status": "FINISHED",
        "end_date": "2024-01-15T11:00:00",
        "task_name": "Test Job",
    }


@pytest.fixture
def sample_band():
    """Create a sample band for raster testing."""
    return Band(name="test band", metadata={"key": "value"})


@pytest.fixture
def sample_raster_results(sample_band):
    """Create sample RasterResults for testing."""
    return RasterResults(
        name="Test Raster",
        rasters={
            "band1": Raster(
                uri=URI(uri=Path("/path/to/raster.tif")),
                bands=[sample_band],
                datatype=DataType.INT16,
                filetype=RasterFileType.GEOTIFF,
            )
        },
    )


@pytest.fixture
def sample_vector_results_generic():
    """Create sample VectorResults with generic vector type."""
    return VectorResults(
        name="Test Generic Vector",
        vector=Vector(
            uri=URI(uri=Path("/path/to/data.geojson")),
            type=VectorType.GENERIC,
        ),
    )


@pytest.fixture
def sample_vector_results_error_recode():
    """Create sample VectorResults with error recode type."""
    return VectorResults(
        name="False positive/negative",
        vector=VectorFalsePositive(
            uri=URI(uri=Path("/path/to/errors.gpkg")),
            type=VectorType.ERROR_RECODE,
        ),
    )


@pytest.fixture
def sample_file_results():
    """Create sample FileResults for testing."""
    return FileResults(
        name="Test File",
        uri=URI(uri=Path("/path/to/file.xlsx")),
    )


@pytest.fixture
def sample_json_results():
    """Create sample JsonResults for testing."""
    return JsonResults(
        name="Test JSON",
        data={"key": "value", "count": 42},
    )


# =============================================================================
# Job with Single Results Tests
# =============================================================================


class TestJobSingleResults:
    """Tests for Job with a single result object."""

    def test_job_with_single_raster_results(self, base_job_data, sample_raster_results):
        """Test Job serialization/deserialization with single RasterResults."""
        base_job_data["results"] = sample_raster_results.Schema().dump(
            sample_raster_results
        )

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, RasterResults)
        assert loaded.results.name == "Test Raster"
        assert loaded.is_raster()
        assert not loaded.is_vector()

    def test_job_with_single_vector_results(
        self, base_job_data, sample_vector_results_generic
    ):
        """Test Job with single VectorResults."""
        base_job_data["results"] = sample_vector_results_generic.Schema().dump(
            sample_vector_results_generic
        )

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, VectorResults)
        assert loaded.results.vector.type == VectorType.GENERIC
        assert loaded.is_vector()
        assert not loaded.is_raster()

    def test_job_with_single_vector_error_recode(
        self, base_job_data, sample_vector_results_error_recode
    ):
        """Test Job with single VectorResults containing VectorFalsePositive."""
        base_job_data["results"] = sample_vector_results_error_recode.Schema().dump(
            sample_vector_results_error_recode
        )

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, VectorResults)
        assert loaded.results.vector.type == VectorType.ERROR_RECODE

    def test_job_with_null_results(self, base_job_data):
        """Test Job with null results."""
        base_job_data["results"] = None

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert loaded.results is None
        assert not loaded.is_raster()
        assert not loaded.is_vector()

    def test_job_with_empty_results(self, base_job_data):
        """Test Job with EmptyResults."""
        empty = EmptyResults(name="Empty")
        base_job_data["results"] = EmptyResults.Schema().dump(empty)

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, EmptyResults)


# =============================================================================
# Job with List of Results Tests
# =============================================================================


class TestJobListResults:
    """Tests for Job with a list of result objects."""

    def test_job_with_list_of_raster_results(self, base_job_data, sample_band):
        """Test Job with list containing multiple RasterResults."""
        raster1 = RasterResults(
            name="Raster 1",
            rasters={
                "band1": Raster(
                    uri=URI(uri=Path("/path/to/raster1.tif")),
                    bands=[sample_band],
                    datatype=DataType.INT16,
                    filetype=RasterFileType.GEOTIFF,
                )
            },
        )
        raster2 = RasterResults(
            name="Raster 2",
            rasters={
                "band1": Raster(
                    uri=URI(uri=Path("/path/to/raster2.tif")),
                    bands=[sample_band],
                    datatype=DataType.INT16,
                    filetype=RasterFileType.GEOTIFF,
                )
            },
        )

        base_job_data["results"] = [
            raster1.Schema().dump(raster1),
            raster2.Schema().dump(raster2),
        ]

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, list)
        assert len(loaded.results) == 2
        assert all(isinstance(r, RasterResults) for r in loaded.results)
        assert loaded.is_raster()

    def test_job_with_mixed_results_list(
        self,
        base_job_data,
        sample_raster_results,
        sample_vector_results_generic,
        sample_vector_results_error_recode,
    ):
        """Test Job with list containing mixed result types."""
        base_job_data["results"] = [
            sample_raster_results.Schema().dump(sample_raster_results),
            sample_vector_results_generic.Schema().dump(sample_vector_results_generic),
            sample_vector_results_error_recode.Schema().dump(
                sample_vector_results_error_recode
            ),
        ]

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert isinstance(loaded.results, list)
        assert len(loaded.results) == 3
        assert loaded.is_raster()
        assert loaded.is_vector()

        # Check individual result types
        raster_results = loaded.get_results_by_type(RasterResults)
        assert len(raster_results) == 1

        vector_results = loaded.get_results_by_type(VectorResults)
        assert len(vector_results) == 2

    def test_job_with_empty_list(self, base_job_data):
        """Test Job with empty results list."""
        base_job_data["results"] = []

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        assert loaded.results == []
        assert not loaded.is_raster()
        assert not loaded.is_vector()

    def test_job_with_raster_and_vector_results(
        self, base_job_data, sample_raster_results, sample_vector_results_error_recode
    ):
        """Test Job with combined raster and error recode vector results."""
        base_job_data["results"] = [
            sample_raster_results.Schema().dump(sample_raster_results),
            sample_vector_results_error_recode.Schema().dump(
                sample_vector_results_error_recode
            ),
        ]

        schema = Job.Schema()
        loaded = schema.load(base_job_data)

        # Get the vector result and verify it's the error recode type
        vector_result = loaded.get_first_result_by_type(VectorResults)
        assert vector_result is not None
        assert vector_result.vector.type == VectorType.ERROR_RECODE

        # Verify raster is also present
        raster_result = loaded.get_first_result_by_type(RasterResults)
        assert raster_result is not None


# =============================================================================
# Job Results Helper Method Tests
# =============================================================================


class TestJobResultsHelpers:
    """Tests for Job results helper methods."""

    def test_get_results_list_single_result(self, base_job_data, sample_raster_results):
        """Test _get_results_list with single result."""
        base_job_data["results"] = sample_raster_results.Schema().dump(
            sample_raster_results
        )
        job = Job.Schema().load(base_job_data)

        results_list = job._get_results_list()
        assert isinstance(results_list, list)
        assert len(results_list) == 1
        assert isinstance(results_list[0], RasterResults)

    def test_get_results_list_already_list(self, base_job_data, sample_raster_results):
        """Test _get_results_list when results is already a list."""
        base_job_data["results"] = [
            sample_raster_results.Schema().dump(sample_raster_results),
        ]
        job = Job.Schema().load(base_job_data)

        results_list = job._get_results_list()
        assert isinstance(results_list, list)
        assert len(results_list) == 1

    def test_get_results_list_none(self, base_job_data):
        """Test _get_results_list when results is None."""
        base_job_data["results"] = None
        job = Job.Schema().load(base_job_data)

        results_list = job._get_results_list()
        assert results_list == []

    def test_get_results_by_type(
        self, base_job_data, sample_raster_results, sample_vector_results_generic
    ):
        """Test get_results_by_type method."""
        base_job_data["results"] = [
            sample_raster_results.Schema().dump(sample_raster_results),
            sample_vector_results_generic.Schema().dump(sample_vector_results_generic),
        ]
        job = Job.Schema().load(base_job_data)

        vectors = job.get_results_by_type(VectorResults)
        assert len(vectors) == 1
        assert isinstance(vectors[0], VectorResults)

    def test_get_first_result_by_type_found(
        self, base_job_data, sample_vector_results_generic
    ):
        """Test get_first_result_by_type when result exists."""
        base_job_data["results"] = sample_vector_results_generic.Schema().dump(
            sample_vector_results_generic
        )
        job = Job.Schema().load(base_job_data)

        result = job.get_first_result_by_type(VectorResults)
        assert result is not None
        assert isinstance(result, VectorResults)

    def test_get_first_result_by_type_not_found(
        self, base_job_data, sample_raster_results
    ):
        """Test get_first_result_by_type when result doesn't exist."""
        base_job_data["results"] = sample_raster_results.Schema().dump(
            sample_raster_results
        )
        job = Job.Schema().load(base_job_data)

        result = job.get_first_result_by_type(VectorResults)
        assert result is None


# =============================================================================
# Job Roundtrip Tests
# =============================================================================


class TestJobRoundtrip:
    """Tests for Job serialize/deserialize roundtrip."""

    def test_job_roundtrip_single_vector_result(
        self, base_job_data, sample_vector_results_error_recode
    ):
        """Test Job roundtrip with single VectorResults."""
        base_job_data["results"] = sample_vector_results_error_recode.Schema().dump(
            sample_vector_results_error_recode
        )

        schema = Job.Schema()
        loaded = schema.load(base_job_data)
        dumped = schema.dump(loaded)
        reloaded = schema.load(dumped)

        assert isinstance(reloaded.results, VectorResults)
        assert reloaded.results.vector.type == VectorType.ERROR_RECODE

    def test_job_roundtrip_list_results(
        self, base_job_data, sample_raster_results, sample_vector_results_generic
    ):
        """Test Job roundtrip with list of results."""
        base_job_data["results"] = [
            sample_raster_results.Schema().dump(sample_raster_results),
            sample_vector_results_generic.Schema().dump(sample_vector_results_generic),
        ]

        schema = Job.Schema()
        loaded = schema.load(base_job_data)
        dumped = schema.dump(loaded)
        reloaded = schema.load(dumped)

        assert isinstance(reloaded.results, list)
        assert len(reloaded.results) == 2
        assert reloaded.is_raster()
        assert reloaded.is_vector()


# =============================================================================
# ResultsField Tests
# =============================================================================


class TestResultsField:
    """Tests for the custom ResultsField marshmallow field."""

    def test_results_field_deserialize_single(self):
        """Test ResultsField deserializes single result correctly."""
        field = ResultsField()
        data = {
            "type": "RasterResults",
            "name": "Test",
            "rasters": {},
        }

        result = field._deserialize(data, None, None)
        assert isinstance(result, RasterResults)

    def test_results_field_deserialize_list(self):
        """Test ResultsField deserializes list of results correctly."""
        field = ResultsField()
        data = [
            {"type": "RasterResults", "name": "Raster", "rasters": {}},
            {
                "type": "VectorResults",
                "name": "Vector",
                "vector": {"uri": None, "type": "Generic"},
            },
        ]

        result = field._deserialize(data, None, None)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], RasterResults)
        assert isinstance(result[1], VectorResults)

    def test_results_field_serialize_single(self, sample_raster_results):
        """Test ResultsField serializes single result correctly."""
        field = ResultsField()
        result = field._serialize(sample_raster_results, None, None)

        assert isinstance(result, dict)
        assert result["type"] == "RasterResults"

    def test_results_field_serialize_list(
        self, sample_raster_results, sample_vector_results_generic
    ):
        """Test ResultsField serializes list of results correctly."""
        field = ResultsField()
        result = field._serialize(
            [sample_raster_results, sample_vector_results_generic], None, None
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "RasterResults"
        assert result[1]["type"] == "VectorResults"

    def test_results_field_none_value(self):
        """Test ResultsField handles None correctly."""
        field = ResultsField()
        assert field._deserialize(None, None, None) is None
        assert field._serialize(None, None, None) is None
