import pytest

from te_schemas.aoi import AOI


def test_valid_geojson_point():
    geojson = {"type": "Point", "coordinates": [125.6, 10.1]}
    aoi = AOI(geojson)
    assert aoi.is_valid()  # Assuming AOI class has an is_valid method


def test_invalid_geojson():
    geojson = {"type": "InvalidType", "coordinates": [125.6, 10.1]}
    with pytest.raises(ValueError):
        AOI(geojson)


def test_geojson_missing_coordinates():
    geojson = {"type": "Point"}
    with pytest.raises(ValueError):
        AOI(geojson)


def test_geojson_with_properties():
    geojson = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [125.6, 10.1]},
        "properties": {"name": "Dinagat Islands"},
    }
    aoi = AOI(geojson)
    assert aoi.geojson["features"][0]["properties"]["name"] == "Dinagat Islands"


def test_valid_geojson_polygon():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[125.6, 10.1], [125.7, 10.1], [125.7, 10.2], [125.6, 10.2], [125.6, 10.1]]
        ],
    }
    aoi = AOI(geojson)
    assert aoi.is_valid()


def test_valid_geojson_featurecollection():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [125.6, 10.1]},
                "properties": {"name": "Dinagat Islands"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [125.6, 10.1],
                            [125.7, 10.1],
                            [125.7, 10.2],
                            [125.6, 10.2],
                            [125.6, 10.1],
                        ]
                    ],
                },
                "properties": {"name": "Polygon Feature"},
            },
        ],
    }
    aoi = AOI(geojson)
    assert aoi.is_valid()
