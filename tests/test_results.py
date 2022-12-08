from copy import deepcopy
from pathlib import Path
from pathlib import PurePosixPath

import pytest

from te_schemas.results import Band
from te_schemas.results import DataType
from te_schemas.results import Raster
from te_schemas.results import RasterFileType
from te_schemas.results import RasterResults
from te_schemas.results import TiledRaster
from te_schemas.results import URI

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
    tile_uris=[URI("https://test.com/test/test_int16.tif", etag=None)],
    bands=[dummy_Band],
    datatype=DataType.INT16,
    filetype=RasterFileType.GEOTIFF,
)

dummy_TiledRaster_float32 = TiledRaster(
    tile_uris=[URI("https://test.com/test/test_float32.tif", etag=None)],
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


def test_raster_results_combine_tiledraster():
    # Test combine of two RasterResults both with TiledRaster instances

    base = deepcopy(dummy_RasterResults_tiledraster)
    other = deepcopy(base)

    for value in base.rasters.values():
        assert isinstance(value, TiledRaster)
    base.combine(other)
    for value in base.rasters.values():
        assert len(value.tile_uris) == 2
        assert isinstance(value, TiledRaster)


def test_raster_results_combine_tiledraster_raster():
    # Test combine of two RasterResults with one storing a Raster instance, the
    # other a TiledRaster instance

    base = deepcopy(dummy_RasterResults_tiledraster)
    other = deepcopy(dummy_RasterResults_raster)

    base.combine(other)
    for value in base.rasters.values():
        assert len(value.tile_uris) == 2
        assert isinstance(value, TiledRaster)
