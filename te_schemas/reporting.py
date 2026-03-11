import datetime
from dataclasses import field
from typing import Dict, List, Optional

from marshmallow import validate
from marshmallow_dataclass import dataclass

from . import land_cover, schemas
from .error_recode import ErrorRecodePolygons


@dataclass
class HotspotBrightspotProperties:
    name: str
    area: float
    type: str = field(metadata={"validate": validate.OneOf(["hotspot", "brightspot"])})
    process: str
    basis: str
    periods: List[str]


###############################################################################
# False positive / negative


@dataclass
class ErrorClassificationProperties:
    area: float
    type: str = field(
        metadata={"validate": validate.OneOf(["false negative", "false positive"])}
    )
    place_name: str
    process: str
    basis: str
    periods: str = field(
        metadata={"validate": validate.OneOf(["baseline", "reporting", "both"])}
    )


###############################################################################
# Area summary schemas
@dataclass
class Value:
    name: str
    value: float


@dataclass
class ValuesByYearDict:
    name: str
    unit: str
    values: Dict[int, Dict[str, float]]


# Area summary schemas
@dataclass
class Area:
    name: Optional[str]
    area: float = field(metadata={"validate": validate.Range(min=0)})


@dataclass
class AreaList:
    name: Optional[str]
    unit: str = field(metadata={"validate": validate.OneOf(["m", "ha", "sq km"])})
    areas: List[Area]


# Population summary schema
@dataclass
class Population:
    name: Optional[str]
    population: int = field(metadata={"validate": validate.Range(min=0)})
    type: str = field(
        metadata={
            "validate": validate.OneOf(
                ["Total population", "Female population", "Male population"]
            )
        }
    )


@dataclass
class PopulationList:
    name: Optional[str]
    values: List[Population]


@dataclass
class CrossTabEntry:
    """A single cell in a cross-tabulation matrix.

    Each entry represents the area (or other metric) for a specific
    combination of initial and final classification labels.
    """

    #: Classification label for the initial period (rows of the matrix).
    initial_label: str
    #: Classification label for the final period (columns of the matrix).
    final_label: str
    #: Area or metric value for this (initial_label, final_label) combination.
    value: float


@dataclass
class CrossTab:
    """A cross-tabulation of land area by two classification layers.

    Used to summarise how land area is distributed across combinations of
    an initial-period classification (rows) and a final-period
    classification (columns).
    """

    name: Optional[str]
    unit: str
    #: Start year of the initial (baseline) period.
    initial_year: int
    #: End year of the final (reporting) period.
    final_year: int
    #: List of cross-tabulation entries, one per (row, column) cell.
    values: List[CrossTabEntry]


@dataclass
class CrossTabEntryInitialFinal:
    initial_label: str
    final_label: str
    initial_value: float
    final_value: float


@dataclass
class CrossTabInitialFinal:
    name: Optional[str]
    unit: str
    initial_year: int
    final_year: int
    values: List[CrossTabEntryInitialFinal]


###
# Schemas to facilitate UNCCD reporting
@dataclass
class ReportMetadata:
    title: str
    date: datetime.datetime
    trends_earth_version: schemas.TrendsEarthVersion
    area_of_interest: schemas.AreaOfInterest
    affected_areas_only: bool = field(default=False)

    class Meta:
        datetimeformat = "%Y-%m-%dT%H:%M:%S+00:00"


@dataclass
class SDG15Report:
    """Summary report on SDG Indicator 15.3.1."""

    summary: AreaList


@dataclass
class ProductivityReport:
    """Report on land productivity within a particular period."""

    summaries: Dict[str, AreaList]
    crosstabs_by_productivity_class: List[CrossTab]


@dataclass
class LandCoverReport:
    """Report on land cover within a particular period."""

    summary: AreaList
    legend_nesting: land_cover.LCLegendNesting
    transition_matrix: land_cover.LCTransitionDefinitionDeg
    crosstabs_by_land_cover_class: List[CrossTab]
    land_cover_areas_by_year: ValuesByYearDict


@dataclass
class SoilOrganicCarbonReport:
    """Report on soil organic carbon within a particular period."""

    #: Summary statistics on change in soil organic carbon, stored as a `dict`,
    #: where keys indicate summary type (over "all_cover_types" or
    #: "non_water"), and values indicate areas improved, stable, degraded, or no
    #: data.
    summaries: Dict[str, AreaList]
    #: Soil organic carbon stock by year and land cover class
    soc_stock_by_year: ValuesByYearDict


@dataclass
class LandConditionAssessment:
    """Report on land condition within a particular period."""

    #: Summary statistics on SDG Indicator 15.3.1.
    sdg: SDG15Report
    #: Report on land productivity.
    productivity: ProductivityReport
    #: Report on land cover.
    land_cover: LandCoverReport
    #: Report on soil organic carbon.
    soil_organic_carbon: SoilOrganicCarbonReport
    #: Polygons indicating false positives and false negatives in the SDG Indicator 15.3.1 layer.
    error_recode: Optional[ErrorRecodePolygons] = field(default=None)
    #: Summary statistics on false positive/negative areas.
    sdg_error_recode: Optional[AreaList] = field(default=None)


@dataclass
class LandConditionStatus:
    """Report on land condition for a particular period, relative to baseline."""

    #: Summary statistics on SDG Indicator 15.3.1.
    sdg: AreaList
    #: Report on land productivity.
    productivity: Dict[str, AreaList]
    #: Report on land cover.
    land_cover: AreaList
    #: Report on soil organic carbon.
    soil_organic_carbon: Dict[str, AreaList]


@dataclass
class LandConditionChange:
    """Cross-tabulation of baseline vs reporting-period assessment.

    Each field is a cross-tabulation whose rows represent the
    baseline-period indicator assessment (Improved / Stable / Degraded)
    and whose columns represent the reporting-period indicator assessment
    (Improved / Stable / Degraded).  Cell values are land areas. No data
    may also be included as a category.
    """

    #: Baseline vs reporting-period assessment for the combined SDG 15.3.1
    #: indicator (one-out, all-out rule across productivity, land cover,
    #: and soil organic carbon).
    sdg: CrossTab
    #: Baseline vs reporting-period assessment for land productivity.
    productivity: CrossTab
    #: Baseline vs reporting-period assessment for land cover.
    land_cover: CrossTab
    #: Baseline vs reporting-period assessment for soil organic carbon.
    soil_organic_carbon: CrossTab


@dataclass
class LandConditionReport:
    """Full land-condition report for one reporting period.

    Combines three complementary views of land condition:

    *  ``period_assessment`` – per-period indicator values and summaries
       (improved / stable / degraded areas for each sub-indicator).
    *  ``status_assessment`` – final degradation *status* after applying
       the 3×3 reclassification rule to derive status from baseline and
       reporting-period assessments.
    *  ``change_assessment`` – 3×3 cross-tabulations of baseline
       assessment (rows) vs reporting-period assessment (columns) for
       each sub-indicator.  These are the raw inputs to the status rule.
    """

    #: Indicator-level assessment for this period (areas by class for
    #: SDG, productivity, land cover, and soil organic carbon).
    period_assessment: LandConditionAssessment
    #: Degradation status derived by applying the UNCCD 3×3
    #: reclassification rule to baseline and reporting-period assessments.
    status_assessment: Optional[LandConditionStatus] = field(default=None)
    #: Cross-tabulations of baseline vs reporting-period assessment
    #: (one per sub-indicator).  These are the inputs used to derive
    #: ``status_assessment``.
    change_assessment: Optional[LandConditionChange] = field(default=None)


@dataclass
class AffectedPopulationReport:
    summary: Dict[str, PopulationList]


@dataclass
class DroughtExposedPopulation:
    drought_class: str = field(
        metadata={
            "validate": validate.OneOf(
                [
                    "Mild drought",
                    "Moderate drought",
                    "Severe drought",
                    "Extreme drought",
                    "Non-drought",
                ]
            )
        }
    )
    year: int
    exposed_population: List[Population]


@dataclass
class DroughtReport:
    tier_one: Dict[int, AreaList]
    tier_two: Dict[int, Dict[str, PopulationList]]
    tier_three: Dict[int, Value]


@dataclass
class TrendsEarthLandConditionSummary:
    metadata: ReportMetadata
    land_condition: Dict[str, LandConditionReport]
    affected_population: Dict[str, AffectedPopulationReport]


@dataclass
class TrendsEarthDroughtSummary:
    metadata: ReportMetadata
    drought: DroughtReport
