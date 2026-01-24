from copy import deepcopy
from pathlib import Path, PurePosixPath

import pytest

from te_schemas.results import (
    URI,
    Band,
    DataType,
    Raster,
    RasterFileType,
    RasterResults,
    ResultType,
    TiledRaster,
    Vector,
    VectorFalsePositive,
    VectorResults,
    VectorType,
)

dummy_Band = Band(name="dummy band", metadata={"test_metadata_key": "test metadata"})

dummy_Raster_int16 = Raster(
    uri=URI("https://test.com/test/test_int16.tif", etag=None),
    bands=[dummy_Band],
    datatype=DataType.INT16,
    filetype=RasterFileType.GEOTIFF,
)

dummy_Raster_float32 = Raster(
    uri=URI("https://test.com/test/test_float32.tif", etag=None),
    bands=[dummy_Band],
    datatype=DataType.FLOAT32,
    filetype=RasterFileType.GEOTIFF,
)

dummy_TiledRaster_int16 = TiledRaster(
    tile_uris=[
        URI("https://test.com/test/test_int16_1.tif", etag=None),
        URI("https://test.com/test/test_int16_2.tif", etag=None),
    ],
    bands=[dummy_Band],
    datatype=DataType.INT16,
    filetype=RasterFileType.GEOTIFF,
)

dummy_TiledRaster_float32 = TiledRaster(
    tile_uris=[
        URI("https://test.com/test/test_float32_1.tif", etag=None),
        URI("https://test.com/test/test_float32_2.tif", etag=None),
    ],
    bands=[dummy_Band],
    datatype=DataType.FLOAT32,
    filetype=RasterFileType.GEOTIFF,
)

dummy_RasterResults_raster = RasterResults(
    name="dummy raster results",
    rasters={"INT16": dummy_Raster_int16, "FLOAT32": dummy_Raster_float32},
    uri=URI("https://test.com/test/test.tif", etag=None),
    data={},
)

dummy_RasterResults_tiledraster = RasterResults(
    name="dummy raster results",
    rasters={"INT16": dummy_TiledRaster_int16, "FLOAT32": dummy_TiledRaster_float32},
    uri=URI("https://test.com/test/test.tif", etag=None),
    data={},
)


def test_uri_from_vsifilepath():
    assert URI.Schema().dump(URI(PurePosixPath("/vsis3/test/test.tif"), None)) == {
        "etag": None,
        "uri": "/vsis3/test/test.tif",
    }

    assert URI(PurePosixPath("/vsis3/test/test.tif"), etag=None) == URI.Schema().load(
        {"uri": PurePosixPath("/vsis3/test/test.tif")}
    )


def test_uri_from_filepath():
    assert URI.Schema().dump(URI(Path("/home/test/test.tif"), None)) == {
        "etag": None,
        "uri": str(Path("/home/test/test.tif")),
    }

    assert URI(Path("/home/test/test.tif"), etag=None) == URI.Schema().load(
        {"uri": Path("/home/test/test.tif")}
    )


def test_uri_from_url():
    assert URI.Schema().dump(URI("https://test.com/test/test.tif", None)) == {
        "etag": None,
        "uri": "https://test.com/test/test.tif",
    }

    assert URI("https://test.com/test/test.tif", etag=None) == URI.Schema().load(
        {"uri": "https://test.com/test/test.tif"}
    )


def test_uri_from_invalid_values():
    with pytest.raises(TypeError):
        URI.Schema().dump(URI("/home/test/test.tif"), None)

    with pytest.raises(TypeError):
        URI.Schema().dump(URI("/vsis3/test/test.tif"), None)


def test_raster_results_combine_raster():
    # Test combine of two RasterResults storing Raster instances
    base = deepcopy(dummy_RasterResults_raster)
    other = deepcopy(base)

    for value in base.rasters.values():
        assert isinstance(value, Raster)
    base.combine(other)
    for value in base.rasters.values():
        assert len(value.tile_uris) == 2
        assert isinstance(value, TiledRaster)
    RasterResults.Schema().dump(base)


def test_raster_results_combine_tiledraster():
    # Test combine of two RasterResults both with TiledRaster instances

    base = deepcopy(dummy_RasterResults_tiledraster)
    other = deepcopy(base)

    for value in base.rasters.values():
        assert isinstance(value, TiledRaster)
    base.combine(other)
    for value in base.rasters.values():
        assert len(value.tile_uris) == 4
        assert isinstance(value, TiledRaster)
    RasterResults.Schema().dump(base)


def test_raster_results_combine_tiledraster_raster():
    # Test combine of two RasterResults with one storing a Raster instance, the
    # other a TiledRaster instance

    base = deepcopy(dummy_RasterResults_tiledraster)
    other = deepcopy(dummy_RasterResults_raster)

    base.combine(other)
    for value in base.rasters.values():
        assert len(value.tile_uris) == 3
        assert isinstance(value, TiledRaster)
    RasterResults.Schema().dump(base)


# =============================================================================
# Vector and VectorResults Tests
# =============================================================================


class TestVector:
    """Tests for the Vector base class."""

    def test_vector_serialize_with_uri(self):
        """Test serializing a Vector with a URI."""
        vector = Vector(
            uri=URI(uri=Path("/path/to/file.geojson")),
            type=VectorType.GENERIC,
        )
        schema = Vector.Schema()
        dumped = schema.dump(vector)

        assert dumped["type"] == "Generic"
        assert dumped["uri"]["uri"] == str(Path("/path/to/file.geojson"))

    def test_vector_serialize_with_none_uri(self):
        """Test serializing a Vector with None URI."""
        vector = Vector(uri=None, type=VectorType.GENERIC)
        schema = Vector.Schema()
        dumped = schema.dump(vector)

        assert dumped["type"] == "Generic"
        assert dumped["uri"] is None

    def test_vector_deserialize(self):
        """Test deserializing a Vector."""
        data = {
            "uri": {"uri": "/path/to/file.geojson", "etag": None},
            "type": "Generic",
        }
        schema = Vector.Schema()
        loaded = schema.load(data)

        assert isinstance(loaded, Vector)
        assert loaded.type == VectorType.GENERIC
        assert loaded.uri is not None

    def test_vector_deserialize_with_none_uri(self):
        """Test deserializing a Vector with None URI."""
        data = {"uri": None, "type": "Generic"}
        schema = Vector.Schema()
        loaded = schema.load(data)

        assert isinstance(loaded, Vector)
        assert loaded.uri is None

    def test_vector_roundtrip(self):
        """Test serialize/deserialize roundtrip for Vector."""
        original = Vector(
            uri=URI(uri=Path("/test/path.geojson")),
            type=VectorType.GENERIC,
        )
        schema = Vector.Schema()
        dumped = schema.dump(original)
        loaded = schema.load(dumped)

        assert loaded.type == original.type
        assert loaded.uri.uri == original.uri.uri


class TestVectorFalsePositive:
    """Tests for the VectorFalsePositive subclass."""

    def test_vectorfalsepositive_default_type(self):
        """Test that VectorFalsePositive defaults to ERROR_RECODE type."""
        vfp = VectorFalsePositive(uri=None)
        assert vfp.type == VectorType.ERROR_RECODE

    def test_vectorfalsepositive_serialize(self):
        """Test serializing VectorFalsePositive."""
        vfp = VectorFalsePositive(
            uri=URI(uri=Path("/path/to/errors.geojson")),
            type=VectorType.ERROR_RECODE,
        )
        schema = VectorFalsePositive.Schema()
        dumped = schema.dump(vfp)

        assert dumped["type"] == "False positive/negative"
        assert dumped["uri"]["uri"] == str(Path("/path/to/errors.geojson"))

    def test_vectorfalsepositive_deserialize(self):
        """Test deserializing VectorFalsePositive."""
        data = {
            "uri": {"uri": "/path/to/errors.geojson", "etag": None},
            "type": "False positive/negative",
        }
        schema = VectorFalsePositive.Schema()
        loaded = schema.load(data)

        assert isinstance(loaded, VectorFalsePositive)
        assert loaded.type == VectorType.ERROR_RECODE

    def test_vectorfalsepositive_roundtrip(self):
        """Test serialize/deserialize roundtrip for VectorFalsePositive."""
        original = VectorFalsePositive(
            uri=URI(uri=Path("/test/errors.gpkg")),
            type=VectorType.ERROR_RECODE,
        )
        schema = VectorFalsePositive.Schema()
        dumped = schema.dump(original)
        loaded = schema.load(dumped)

        assert loaded.type == VectorType.ERROR_RECODE
        assert loaded.uri.uri == original.uri.uri


class TestVectorResults:
    """Tests for VectorResults with the new Vector-based structure."""

    def test_vectorresults_with_generic_vector(self):
        """Test VectorResults containing a generic Vector."""
        vr = VectorResults(
            name="Test Generic Vector",
            vector=Vector(
                uri=URI(uri=Path("/path/to/data.geojson")),
                type=VectorType.GENERIC,
            ),
        )
        assert vr.vector.type == VectorType.GENERIC
        assert vr.uri == vr.vector.uri  # uri property should delegate to vector.uri

    def test_vectorresults_with_error_recode_vector(self):
        """Test VectorResults containing a VectorFalsePositive."""
        vr = VectorResults(
            name="False positive/negative",
            vector=VectorFalsePositive(
                uri=URI(uri=Path("/path/to/errors.gpkg")),
                type=VectorType.ERROR_RECODE,
            ),
        )
        assert vr.vector.type == VectorType.ERROR_RECODE
        assert isinstance(vr.vector, VectorFalsePositive)

    def test_vectorresults_uri_property(self):
        """Test that the uri property correctly delegates to vector.uri."""
        uri = URI(uri=Path("/test/file.geojson"))
        vr = VectorResults(
            name="Test",
            vector=Vector(uri=uri, type=VectorType.GENERIC),
        )
        # Property should return the same object
        assert vr.uri is vr.vector.uri
        assert vr.uri.uri == Path("/test/file.geojson")

    def test_vectorresults_uri_property_none(self):
        """Test uri property when vector.uri is None."""
        vr = VectorResults(
            name="Test",
            vector=Vector(uri=None, type=VectorType.GENERIC),
        )
        assert vr.uri is None

    def test_vectorresults_serialize(self):
        """Test serializing VectorResults."""
        vr = VectorResults(
            name="Test Vector Results",
            vector=Vector(
                uri=URI(uri=Path("/path/to/data.geojson")),
                type=VectorType.GENERIC,
            ),
            extent=(0.0, 0.0, 10.0, 10.0),
        )
        schema = VectorResults.Schema()
        dumped = schema.dump(vr)

        assert dumped["name"] == "Test Vector Results"
        assert dumped["type"] == "VectorResults"
        assert dumped["vector"]["type"] == "Generic"
        assert tuple(dumped["extent"]) == (0.0, 0.0, 10.0, 10.0)

    def test_vectorresults_deserialize(self):
        """Test deserializing VectorResults."""
        data = {
            "name": "Test Vector",
            "vector": {
                "uri": {"uri": "/path/to/file.geojson", "etag": None},
                "type": "Generic",
            },
            "extent": None,
            "type": "VectorResults",
        }
        schema = VectorResults.Schema()
        loaded = schema.load(data)

        assert isinstance(loaded, VectorResults)
        assert loaded.name == "Test Vector"
        assert loaded.vector.type == VectorType.GENERIC
        assert loaded.type == ResultType.VECTOR_RESULTS

    def test_vectorresults_deserialize_error_recode(self):
        """Test deserializing VectorResults with error recode type."""
        data = {
            "name": "False positive/negative",
            "vector": {
                "uri": {"uri": "/path/to/errors.gpkg", "etag": None},
                "type": "False positive/negative",
            },
            "extent": (1.0, 2.0, 3.0, 4.0),
            "type": "VectorResults",
        }
        schema = VectorResults.Schema()
        loaded = schema.load(data)

        assert loaded.vector.type == VectorType.ERROR_RECODE

    def test_vectorresults_roundtrip(self):
        """Test serialize/deserialize roundtrip for VectorResults."""
        original = VectorResults(
            name="Roundtrip Test",
            vector=VectorFalsePositive(
                uri=URI(uri=Path("/test/errors.geojson")),
                type=VectorType.ERROR_RECODE,
            ),
            extent=(10.0, 20.0, 30.0, 40.0),
        )
        schema = VectorResults.Schema()
        dumped = schema.dump(original)
        loaded = schema.load(dumped)

        assert loaded.name == original.name
        assert loaded.vector.type == original.vector.type
        assert loaded.extent == original.extent

    def test_vectorresults_backward_compat_ignores_vector_type(self):
        """Test that old format with vector_type field is handled gracefully."""
        # Old format had vector_type at top level - should be ignored
        old_format = {
            "name": "Old Format Test",
            "vector": {
                "uri": {"uri": "/path/to/file.geojson", "etag": None},
                "type": "Generic",
            },
            "vector_type": "Generic",  # Old field - should be ignored
            "extent": None,
            "type": "VectorResults",
        }
        schema = VectorResults.Schema()
        loaded = schema.load(old_format)

        assert loaded.name == "Old Format Test"
        assert loaded.vector.type == VectorType.GENERIC
        # vector_type should not exist on new object
        assert (
            not hasattr(loaded, "vector_type")
            or getattr(loaded, "vector_type", None) is None
        )

    def test_vectorresults_backward_compat_with_old_uri_field(self):
        """Test backward compatibility when old format had uri at top level."""
        old_format = {
            "name": "Old URI Format",
            "uri": {"uri": "/old/path.geojson", "etag": None},  # Old top-level uri
            "vector": {
                "uri": {"uri": "/path/to/file.geojson", "etag": None},
                "type": "False positive/negative",
            },
            "type": "VectorResults",
        }
        schema = VectorResults.Schema()
        loaded = schema.load(old_format)

        # Should use vector.uri, ignoring old top-level uri
        assert loaded.vector.type == VectorType.ERROR_RECODE

    def test_vectorresults_modify_uri_via_property(self):
        """Test that modifying uri.uri through the property works."""
        vr = VectorResults(
            name="Test",
            vector=Vector(
                uri=URI(uri=Path("/original/path.geojson")),
                type=VectorType.GENERIC,
            ),
        )
        # Modify via property (this modifies the underlying URI object)
        vr.uri.uri = Path("/new/path.geojson")

        # Both should reflect the change
        assert vr.uri.uri == Path("/new/path.geojson")
        assert vr.vector.uri.uri == Path("/new/path.geojson")
