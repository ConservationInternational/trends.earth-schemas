import json

from osgeo import ogr, gdal

from . import logger

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

# TODO: Doesn't yet work on points
class AOI(object):
    def __init__(self, geojson):
        self._geojson = geojson
        self._geometry = ogr.CreateGeometryFromJson(geojson)


    def meridian_split(self, as_extent=False, out_format='geojson'):
        """
        Return list of bounding boxes in WGS84 as geojson or WKT

        Returns multiple geometries as needed to avoid having an extent
        crossing the 180th meridian
        """

        if out_format not in ['geojson', 'wkt']:
            raise ValueError(f'Unrecognized out_format "{out_format}')

        hemi_e = ogr.CreateGeometryFromWkt(
            'POLYGON ((0 -90, 0 90, 180 90, 180 -90, 0 -90))')
        hemi_w = ogr.CreateGeometryFromWkt(
            'POLYGON ((-180 -90, -180 90, 0 90, 0 -90, -180 -90))')
        intersections = [
            hemi.Intersection(self._geometry) for hemi in [hemi_e, hemi_w]
        ]

        if as_extent:
            pieces = [
                _get_bounding_box_geom(i)
                for i in intersections if not i.IsEmpty()
            ]
        else:
            pieces = [
                i for i in intersections if not i.IsEmpty()
            ]

        pieces_union = pieces[0].Clone()

        for piece in pieces[1:]:
            pieces_union = pieces_union.Union(piece)
        pieces_bounding = _get_bounding_box_geom(pieces_union)

        total_pieces_area = sum([piece.GetArea() for piece in pieces])
        logger.debug(f'total_pieces_area: {total_pieces_area}')
        logger.debug(f'len(pieces): {len(pieces)}')
        logger.debug(f'pieces_bounding.GetArea(): {pieces_bounding.GetArea()}')

        if (
            (
                not pieces_bounding.GetArea() > total_pieces_area
            ) and (
                (len(pieces) == 1) or
                (total_pieces_area > (pieces_union.GetArea() / 2))
            )
        ):
            # If there is no area in one of the hemispheres, return the
            # original layer, or extent of the original layer. Also return the
            # original layer (or extent) if the area of the combined pieces
            # from both hemispheres is not significantly smaller than that of
            # the original polygon.
            logger.info("AOI being processed in one piece "
                        "(does not cross 180th meridian)")

            out = [pieces_union]
        else:
            logger.info("AOI crosses 180th meridian "
                        "- splitting AOI into two geojsons.")

            out = pieces

        if out_format == 'geojson':
            return [json.loads(o.ExportToJson()) for o in out]
        elif out_format == 'wkt':
            return [o.ExportToWkt() for o in out]

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
                geom = ogr.CreateGeometryFromJson(geojson)
                (minx, maxx, miny, maxy) = geom.GetEnvelope()
                gt = gdal.Open(f).GetGeoTransform()
                left = minx - (minx - gt[0]) % gt[1]
                right = maxx + (gt[1] - ((maxx - gt[0]) % gt[1]))
                bottom = miny + (gt[5] - ((miny - gt[3]) % gt[5]))
                top = maxy - (maxy - gt[3]) % gt[5]
                out.append([left, bottom, right, top])

        return out

    def get_crs_wkt(self):
        return self._geometry.GetSpatialReference().ExportToWkt()

    def bounding_box_geom(self):
        'Returns bounding box in chosen destination coordinate system'

        return _get_bounding_box_geom(self._geometry)

    def bounding_box_gee_geojson(self):
        '''
        Returns list of bounding box geojsons.
        '''

        if self.datatype == 'polygon':
            return self.meridian_split()
        elif self.datatype == 'point':
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
                logger.info('Layer only has one point')

                return [json.loads(geom.asJson())]
            else:
                logger.info('Layer has many points ({})'.format(n))

                return self.meridian_split()
        else:
            raise RuntimeError(
                f"Failed to process area of interest - unknown geometry "
                f"type: {self._geometry.GetGeometryType()}"
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

        return frac

    def get_geojson(self, split=False):
        out = {"type": "FeatureCollection", "features": []}

        if split:
            out['features'].append(self.meridian_split(as_extent=False))
        else:
            out = self._geojson
        return out
