import logging

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
    with pytest.raises(RuntimeError):
        AOI(geojson)


def test_geojson_with_properties():
    geojson = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [125.6, 10.1]},
        "properties": {"name": "Dinagat Islands"},
    }
    aoi = AOI(geojson)
    assert (
        aoi.get_ds().GetLayer(0).GetFeature(0).GetFieldAsString("name")
        == "Dinagat Islands"
    )


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


def test_meridian_split_no_split_as_extent():
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [125.6, 10.1],
                [125.7, 10.1],
                [125.65, 10.15],
                [125.7, 10.2],
                [125.6, 10.2],
                [125.6, 10.1],
            ]
        ],
    }

    geom_without_point_3 = geom.copy()
    geom_without_point_3["coordinates"][0].remove([125.65, 10.15])

    assert AOI(geom).meridian_split(as_extent=True) == [geom_without_point_3]


def test_meridian_split_no_split():
    aoi = AOI(
        {
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
        }
    )
    assert aoi.get_geojson() == aoi.get_geojson(split=True)
    assert aoi.get_geojson() == AOI(aoi.meridian_split()).get_geojson()


def test_meridian_split():
    part1 = [
        [
            [180.0, -10.0],
            [179.0, -10.0],
            [179.0, 10.0],
            [180.0, 10.0],
            [180.0, -10.0],
        ]
    ]
    part2 = [
        [
            [-180.0, 10.0],
            [-179.0, 10.0],
            [-179.0, -10.0],
            [-180.0, -10.0],
            [-180.0, 10.0],
        ]
    ]
    geom = [
        {
            "type": "MultiPolygon",
            "coordinates": [part1, part2],
        },
    ]
    geoms_split = [
        {
            "type": "Polygon",
            "coordinates": part1,
        },
        {
            "type": "Polygon",
            "coordinates": part2,
        },
    ]

    assert AOI(geom).meridian_split() == geoms_split
    assert AOI(geom).get_geojson(split=True) == AOI(geoms_split).get_geojson()
