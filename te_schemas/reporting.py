import datetime

from dataclasses import field
from typing import List, Optional

from marshmallow_dataclass import dataclass
from marshmallow import validate

from . import schemas, land_cover


# Area summary schemas
@dataclass
class Value:
    name: str
    value: float

    class Meta:
        ordered = True


@dataclass
class AnnualValueList:
    name: str
    year: Optional[int]
    unit: str
    values: List[Value]

    class Meta:
        ordered = True


# Area summary schemas
@dataclass
class Area:
    name: Optional[str]
    area: float = field(metadata={"validate": validate.Range(min=0)})

    class Meta:
        ordered = True


@dataclass
class AreaList:
    name: Optional[str]
    unit: str = field(metadata={'validate':
                      validate.OneOf(["m", "ha", "km sq"])})
    areas: List[Area]

    class Meta:
        ordered = True


# Crosstab summary schemas
@dataclass
class CrossTabEntry:
    initial_label: str
    final_label: str
    value: float

    class Meta:
        ordered = True


@dataclass
class CrossTab:
    name: Optional[str]
    #unit: str = field(metadata={'validate': validate.OneOf(["m", "ha", "km sq"])})
    unit: str
    initial_year: int
    final_year: int
    values: List[CrossTabEntry]

    class Meta:
        ordered = True


###
# Schemas to facilitate UNCCD reporting
@dataclass
class ReportMetadata:
    title: str
    date: datetime.datetime
    trends_earth_version: schemas.TrendsEarthVersion
    area_of_interest: schemas.AreaOfInterest

    class Meta:
        ordered = True
        datetimeformat = '%Y-%m-%dT%H:%M:%S+00:00'


@dataclass
class SDG15Report:
    summary: AreaList

    class Meta:
        ordered = True


@dataclass
class ProductivityReport:
    summary: AreaList
    crosstabs_by_productivity_class: List[CrossTab]

    class Meta:
        ordered = True


@dataclass
class LandCoverReport:
    summary: AreaList
    legend_nesting: land_cover.LCLegendNesting
    transition_matrix: land_cover.LCTransitionDefinitionDeg
    crosstab_by_land_cover_class: CrossTab
    land_cover_areas_by_year: List[AnnualValueList]

    class Meta:
        ordered = True


@dataclass
class SoilOrganicCarbonReport:
    summary: AreaList
    crosstab_by_land_cover_class: CrossTab
    soc_stock_by_year: List[AnnualValueList]

    class Meta:
        ordered = True


@dataclass
class LandConditionReport:
    sdg: SDG15Report
    productivity: ProductivityReport
    land_cover: LandCoverReport
    soil_organic_carbon: SoilOrganicCarbonReport

    class Meta:
        ordered = True


@dataclass
class AffectedPopulationReport:
    pass

    class Meta:
        ordered = True


@dataclass
class DroughtReport:
    pass

    class Meta:
        ordered = True


@dataclass
class TrendsEarthSummary:
    metadata: ReportMetadata
    land_condition: LandConditionReport
    affected_population: AffectedPopulationReport
    drought: DroughtReport

    # TODO: Add datasets needed for reporting (band number and filename)

    class Meta:
        ordered = True
