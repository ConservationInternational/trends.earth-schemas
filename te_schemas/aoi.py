import json
import logging
import os
import tempfile
import uuid

from marshmallow_dataclass import dataclass
from osgeo import gdal, ogr

logger = logging.getLogger(__name__)

ogr.UseExceptions()


def _get_bounding_box_geom(geom):
    (minX, maxX, minY, maxY) = geom.GetEnvelope()
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint_2D(minX, minY)
    ring.AddPoint_2D(maxX, minY)
    ring.AddPoint_2D(maxX, maxY)
    ring.AddPoint_2D(minX, maxY)
    ring.AddPoint_2D(minX, minY)
    poly_envelope = ogr.Geometry(ogr.wkbPolygon)
    poly_envelope.AddGeometry(ring)

    return poly_envelope


def _geojson_to_ds(geojson):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as temp_file:
        temp_file.write(json.dumps(geojson).encode("utf-8"))
        temp_file_path = temp_file.name
    logger.debug(f"Wrote temporary file with geojsons to {temp_file.name}")

    return ogr.Open(temp_file_path)


def _make_temp_name(dir=tempfile.gettempdir()):
    return os.path.join(dir, str(uuid.uuid1()))


def _ds_to_geojson(ds):
    temp_file = _make_temp_name()
    driver = ogr.GetDriverByName("GeoJSON")
    temp_ds = driver.CreateDataSource(temp_file)
    temp_layer = temp_ds.CreateLayer("layer_name", geom_type=ogr.wkbPolygon)
    for aoi_layer in ds:
        for feature in aoi_layer:
            temp_layer.CreateFeature(feature)
    temp_ds = None

    with open(temp_file, "r") as file:
        return json.load(file)


def _clean_geojson(geojson):
    if isinstance(geojson, str):
        geojson = json.loads(geojson)

    if "type" in geojson and geojson["type"] == "FeatureCollection":
        # Feature collection
        geojson = geojson
    elif "type" in geojson and geojson["type"] == "Feature":
        # Single feature
        geojson = {"type": "FeatureCollection", "features": [geojson]}
    elif "type" in geojson and geojson["type"] in [
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    ]:
        # Single geometry
        geojson = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": geojson}],
        }
    elif isinstance(geojson, list):
        if all("type" in g and g["type"] == "Feature" for g in geojson):
            # List of features
            geojson = {"type": "FeatureCollection", "features": geojson}
        else:
            # Assume 'geojson' is a list of geometries
            for g in geojson:
                assert "coordinates" in g
                assert "type" in g
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "id": i, "properties": {}, "geometry": g}
                    for i, g in enumerate(geojson)
                ],
            }
    else:
        raise ValueError

    return geojson


@dataclass
class AOI(object):
    geojson: str

    def __init__(self, geojson):
        aoi = _geojson_to_ds(_clean_geojson(geojson))
        assert aoi.GetLayerCount() == 1
        self.geojson = _ds_to_geojson(aoi)

        if not self.is_valid():
            raise ValueError

    def is_valid(self):
        if not self.geojson:
            return False
        else:
            aoi = self.get_ds()
            for layer in aoi:
                for feature in layer:
                    if not feature.geometry().IsValid():
                        return False
        return True

    @property
    def crs(self):
        return self.get_ds().GetSpatialReference().ExportToWkt()

    def meridian_split(self, as_extent=False, out_format="geojson"):
        """
        Return list of bounding boxes in WGS84 as geojson or WKT

        Returns multiple geometries as needed to avoid having an extent
        crossing the 180th meridian
        """

        logger.debug("Performing meridian split")

        if out_format not in ["geojson", "wkt"]:
            raise ValueError(f'Unrecognized out_format "{out_format}')

        hemi_e = ogr.CreateGeometryFromWkt(
            "POLYGON ((0 -90, 0 90, 180 90, 180 -90, 0 -90))"
        )
        hemi_w = ogr.CreateGeometryFromWkt(
            "POLYGON ((-180 -90, -180 90, 0 90, 0 -90, -180 -90))"
        )

        out = []
        aoi = self.get_ds()
        for layer in aoi:
            for feature in layer:
                geom = feature.geometry()

                intersections = [hemi.Intersection(geom) for hemi in [hemi_e, hemi_w]]
                pieces = [i for i in intersections if not i.IsEmpty()]
                pieces_extents = [_get_bounding_box_geom(i) for i in pieces]
                logger.debug(
                    f"pieces extents: {[g.ExportToWkt() for g in pieces_extents]}"
                )

                if as_extent:
                    split_out = pieces_extents
                    unsplit_out = [_get_bounding_box_geom(geom)]
                else:
                    split_out = pieces
                    unsplit_out = [geom]

                # Perform areal calculations on extents even if output is NOT extents,
                # so that meridian split gives consistent results (in terms of number
                # of pieces) regardless of whether requested output is original
                # polygons or extents
                pieces_extents_union = pieces_extents[0].Clone()

                for piece_extent in pieces_extents[1:]:
                    pieces_extents_union = pieces_extents_union.Union(piece_extent)
                bounding_area_unsplit = _get_bounding_box_geom(
                    pieces_extents_union
                ).GetArea()
                bounding_area_split = sum(
                    [piece_extent.GetArea() for piece_extent in pieces_extents]
                )

                logger.debug(
                    f"len(pieces_extents): {len(pieces_extents)} "
                    f"polygon area {geom.GetArea()}, "
                    f"bounding_area_unsplit: {bounding_area_unsplit} "
                    f"bounding_area_split: {bounding_area_split}"
                )

                if (len(pieces) == 1) or (
                    bounding_area_unsplit < 2 * bounding_area_split
                ):
                    # If there is no area in one of the hemispheres, return the
                    # original layer, or extent of the original layer. Also return the
                    # original layer (or extent) if the area of the combined pieces
                    # from both hemispheres is not significantly smaller than that of
                    # the original polygon.
                    logger.info(
                        "Feature being processed in one piece "
                        "(does not appear to cross 180th meridian)"
                    )
                    this_out = unsplit_out
                else:
                    logger.info(
                        "Feature appears to cross 180th meridian - splitting feature into two geojsons."
                    )
                    this_out = split_out

                if out_format == "geojson":
                    out.extend([json.loads(o.ExportToJson()) for o in this_out])
                elif out_format == "wkt":
                    out.extend([o.ExportToWkt() for o in this_out])
        return out

    def get_aligned_output_bounds(self, f):
        geojsons = self.meridian_split(as_extent=True)

        if not geojsons:
            out = None

        else:
            out = []

            for geojson in geojsons:
                # Compute the pixel-aligned bounding box (slightly larger than
                # aoi).
                # Use this to set bounds in vrt files in order to keep the
                # pixels aligned with the chosen layer
                geom = ogr.CreateGeometryFromJson(str(geojson))
                (geom_minx, geom_maxx, geom_miny, geom_maxy) = geom.GetEnvelope()
                ds = gdal.Open(f)
                img_xmin, img_xres, _, img_ymax, _, img_yres = ds.GetGeoTransform()
                width, height = ds.RasterXSize, ds.RasterYSize
                img_xmax = img_xmin + img_xres * width
                img_ymin = img_ymax + img_yres * height

                logger.debug(
                    "image img_xmin %s, img_xmax %s, img_xres %s, img_y_min %s, img_ymax %s, img_yres %s",
                    img_xmin,
                    img_xmax,
                    img_xres,
                    img_ymin,
                    img_ymax,
                    img_yres,
                )

                logger.debug(
                    "geom geom_minx %s, geom_maxx %s, geom_miny %s, geom_maxy %s",
                    geom_minx,
                    geom_maxx,
                    geom_miny,
                    geom_maxy,
                )
                left = geom_minx - (geom_minx - img_xmin) % img_xres

                if left < -180:
                    left = -180
                right = geom_maxx + (img_xres - ((geom_maxx - img_xmin) % img_xres))

                if right > 180:
                    right = 180
                bottom = geom_miny + (img_yres - ((geom_miny - img_ymax) % img_yres))

                if bottom < -90:
                    bottom = -90
                top = geom_maxy - (geom_maxy - img_ymax) % img_yres

                if top > 90:
                    top = 90
                out.append([left, bottom, right, top])

        logger.debug("aligned output bounds is %s", out)

        return out

    def bounding_box_gee_geojson(self):
        """
        Returns list of bounding box geojsons.
        """

        aoi = self.get_ds()
        datatype = aoi.GetLayer()[0].GetGeomType()
        if datatype == "polygon":
            return self.meridian_split()
        elif datatype == "point":
            # TODO: Code this for OGR

            # If there is only on point, don't calculate an extent (extent of
            # one point is a box with sides equal to zero)
            n = 0

            for f in self.l.getFeatures():
                n += 1

                if n == 1:
                    # Save the first geometry in case it is needed later
                    # for a layer that only has one point in it
                    geom = f.geometry()

            if n == 1:
                logger.info("Layer only has one point")

                return [json.loads(geom.asJson())]
            else:
                logger.info("Layer has many points ({})".format(n))

                return self.meridian_split()
        else:
            raise RuntimeError(
                f"Failed to process area of interest - unknown geometry "
                f"type: {aoi.GetLayer()[0].GetGeomType()}"
            )

    def calc_frac_overlap(self, in_geom):
        """
        Returns fraction of AOI that is overlapped by OGR geometry

        Used to calculate "within" with a tolerance
        """
        aoi_geom = ogr.CreateGeometryFromWkt(self.bounding_box_geom().asWkt())

        geom_area = aoi_geom.GetArea()

        if geom_area == 0:
            # Handle case of a point with zero area
            frac = aoi_geom.Within(in_geom)
        else:
            frac = aoi_geom.Intersection(in_geom).GetArea() / geom_area

        logger.debug("fractional overlap is %s", frac)
        return frac

    def get_ds(self):
        return _geojson_to_ds(self.geojson)

    def get_geojson(self, split=False):
        if split:
            features = self.meridian_split(as_extent=False)
            aoi = _geojson_to_ds(_clean_geojson(features))
        else:
            aoi = self.get_ds()

        return _ds_to_geojson(aoi)
