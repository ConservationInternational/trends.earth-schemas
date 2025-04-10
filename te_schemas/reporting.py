import datetime
from dataclasses import field
from typing import Dict, List, Optional, Union

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


# Crosstab summary schemas
@dataclass
class CrossTabEntry:
    initial_label: str
    final_label: str
    value: float


# Crosstab summary schemas
@dataclass
class CrossTabEntryInitialFinal:
    initial_label: str
    final_label: str
    initial_value: float
    final_value: float


@dataclass
class CrossTab:
    name: Optional[str]
    unit: str
    initial_year: int
    final_year: int
    values: List[CrossTabEntry]


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
    summary: AreaList


@dataclass
class ProductivityReport:
    summaries: Dict[str, AreaList]
    crosstabs_by_productivity_class: List[CrossTab]


@dataclass
class LandCoverReport:
    summary: AreaList
    legend_nesting: land_cover.LCLegendNesting
    transition_matrix: land_cover.LCTransitionDefinitionDeg
    crosstabs_by_land_cover_class: List[CrossTab]
    land_cover_areas_by_year: ValuesByYearDict


@dataclass
class SoilOrganicCarbonReport:
    summaries: Dict[str, AreaList]
    crosstab_by_land_cover_class: CrossTab
    soc_stock_by_year: ValuesByYearDict


@dataclass
class LandConditionReport:
    """Class to hold data on land condition for UNCCD reporting."""

    #: Summary statistics on SDG 15.3.1.
    sdg: Optional[SDG15Report] = field(default=None)
    #: Report on land productivity.
    productivity: Optional[ProductivityReport] = field(default=None)
    #: Report on land cover.
    land_cover: Optional[LandCoverReport] = field(default=None)
    #: Report on soil organic carbon.
    soil_organic_carbon: Optional[SoilOrganicCarbonReport] = field(default=None)
    #: Polygons indicating false positives and false negatives in the SDG Indicator 15.3.1 layer.
    error_recode: Optional[ErrorRecodePolygons] = field(default=None)
    #: Report on soil organic carbon.
    sdg_error_recode: Optional[AreaList] = field(default=None)


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
