"""
Error recode schemas for SDG 15.3.1 land degradation analysis.

This module defines the data structures for error recoding polygons used to
correct misclassified pixels in land degradation indicator calculations.
Error recoding allows users to manually override automated classifications
based on local knowledge or ground-truth data.

Classes:
    ErrorRecodeProperties: Properties for a single error recode polygon.
    ErrorRecodeFeature: A GeoJSON Feature containing an error recode polygon.
    ErrorRecodePolygons: A GeoJSON FeatureCollection of error recode polygons.
"""

import uuid as uuid_module
from dataclasses import field
from typing import ClassVar, Dict, List, Optional, Tuple

from marshmallow import EXCLUDE, validate
from marshmallow_dataclass import dataclass


@dataclass
class ErrorRecodeProperties:
    """
    Properties for an error recode polygon feature.

    Defines what pixels should be recoded within the polygon boundary and
    which time periods the recoding applies to.

    Attributes:
        uuid: Unique identifier for the error polygon.
        periods_affected: List of periods to apply recoding to.
            Valid values: "baseline", "report_1", "report_2".
        location_name: Human-readable name for the error area.
        area_km_sq: Area of the polygon in square kilometers.
        process_driving_change: Description of the process causing misclassification.
        basis_for_judgement: Justification for the correction.
        recode_deg_to: What to recode degraded pixels to.
            None = no change, -32768 = no data, 0 = stable, 1 = improved.
        recode_stable_to: What to recode stable pixels to.
            None = no change, -32768 = no data, -1 = degraded, 1 = improved.
        recode_imp_to: What to recode improved pixels to.
            None = no change, -32768 = no data, -1 = degraded, 0 = stable.
        stats: Optional statistics dictionary for the polygon.
    """

    class Meta:
        unknown = EXCLUDE

    uuid: uuid_module.UUID
    periods_affected: List[str] = field(
        metadata={
            "validate": validate.And(
                validate.Length(min=1),
                lambda x: all(
                    item in ["baseline", "report_1", "report_2"] for item in x
                ),
            ),
        },
    )
    location_name: Optional[str] = None
    area_km_sq: Optional[float] = None
    process_driving_change: Optional[str] = None
    basis_for_judgement: Optional[str] = None
    recode_deg_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, 0, 1])},
    )
    recode_stable_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, -1, 1])},
    )
    recode_imp_to: Optional[int] = field(
        default=None,
        metadata={"validate": validate.OneOf([None, -32768, -1, 0])},
    )
    stats: Optional[dict] = None


@dataclass
class ErrorRecodeFeature:
    """
    A GeoJSON Feature representing a single error recode polygon.

    Attributes:
        geometry: GeoJSON geometry dict (typically a Polygon).
        properties: Error recode properties defining the recoding behavior.
        type: Must be "Feature" per GeoJSON spec.
    """

    class Meta:
        unknown = EXCLUDE

    geometry: dict
    properties: ErrorRecodeProperties
    type: str = field(metadata={"validate": validate.Equal("Feature")})


@dataclass
class ErrorRecodePolygons:
    """
    A GeoJSON FeatureCollection of error recode polygons.

    Used to define areas where SDG 15.3.1 land degradation classifications
    should be manually corrected. Each feature specifies which pixel values
    to recode and for which time periods.

    Attributes:
        features: List of ErrorRecodeFeature objects.
        name: Optional name for the collection.
        crs: Optional coordinate reference system definition.
        type: Must be "FeatureCollection" per GeoJSON spec.

    Class Attributes:
        recode_deg_to_options: Valid values for recoding degraded pixels.
        recode_stable_to_options: Valid values for recoding stable pixels.
        recode_imp_to_options: Valid values for recoding improved pixels.
    """

    class Meta:
        unknown = EXCLUDE

    features: List[ErrorRecodeFeature]
    name: Optional[str]
    crs: Optional[dict]
    type: str = field(metadata={"validate": validate.Equal("FeatureCollection")})

    recode_deg_to_options: ClassVar[Tuple[Optional[int], ...]] = (None, -32768, 0, 1)
    recode_stable_to_options: ClassVar[Tuple[Optional[int], ...]] = (
        None,
        -32768,
        -1,
        1,
    )
    recode_imp_to_options: ClassVar[Tuple[Optional[int], ...]] = (None, -32768, -1, 0)

    @property
    def trans_code_lists(
        self,
    ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """
        Generate lookup tables for recode transformations.

        Creates parallel lists that map transformation codes to the target
        values for each pixel category. Used internally for efficient
        raster recoding operations.

        The transformation code system uses a two-digit scheme where:
            - First digit indicates the source class:
                1 = degraded, 2 = improved, 3 = stable, 0 = unchanged
            - Second digit indicates the target class:
                1 = degraded, 2 = improved, 3 = stable, 0 = unchanged

        So the codes are:
            - recode_deg_to: unchanged=10, stable=12, improved=13
            - recode_stable_to: unchanged=20, degraded=21, improved=23
            - recode_imp_to: unchanged=30, degraded=31, stable=32

        Returns:
            Tuple of four lists:
                - codes: Sequential integer codes (0 to N-1)
                - deg_to: Target values for degraded pixels (-9999 = no change)
                - stable_to: Target values for stable pixels (-9999 = no change)
                - imp_to: Target values for improved pixels (-9999 = no change)

        Note:
            -9999 is used as a sentinel value meaning "no recoding".
            -32768 means "recode to nodata".
        """
        codes: List[int] = []
        deg_to: List[int] = []
        stable_to: List[int] = []
        imp_to: List[int] = []
        n = 0
        for i in range(len(self.recode_deg_to_options)):
            for j in range(len(self.recode_stable_to_options)):
                for k in range(len(self.recode_imp_to_options)):
                    codes.append(n)
                    # Convert None to -9999 for "no recoding" sentinel value
                    # This allows -32768 to mean "recode to nodata" as intended
                    deg_val = (
                        self.recode_deg_to_options[i]
                        if self.recode_deg_to_options[i] is not None
                        else -9999
                    )
                    stable_val = (
                        self.recode_stable_to_options[j]
                        if self.recode_stable_to_options[j] is not None
                        else -9999
                    )
                    imp_val = (
                        self.recode_imp_to_options[k]
                        if self.recode_imp_to_options[k] is not None
                        else -9999
                    )
                    deg_to.append(deg_val)
                    stable_to.append(stable_val)
                    imp_to.append(imp_val)
                    n += 1

        return codes, deg_to, stable_to, imp_to

    @property
    def recode_to_trans_code_dict(
        self,
    ) -> Dict[Tuple[Optional[int], Optional[int], Optional[int]], int]:
        """
        Generate a mapping from recode options to transformation codes.

        Creates a dictionary that maps each unique combination of
        (recode_deg_to, recode_stable_to, recode_imp_to) values to a
        sequential integer code. Used for rasterizing error polygons.

        Returns:
            Dict mapping (deg_to, stable_to, imp_to) tuples to integer codes.
        """
        recode_to_trans_code: Dict[
            Tuple[Optional[int], Optional[int], Optional[int]], int
        ] = {}
        n = 0
        for i in range(len(self.recode_deg_to_options)):
            for j in range(len(self.recode_stable_to_options)):
                for k in range(len(self.recode_imp_to_options)):
                    recode_to_trans_code[
                        (
                            self.recode_deg_to_options[i],
                            self.recode_stable_to_options[j],
                            self.recode_imp_to_options[k],
                        )
                    ] = n
                    n += 1

        return recode_to_trans_code
