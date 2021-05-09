import datetime

from dataclasses import field
from typing import List, Optional

from marshmallow_dataclass import dataclass
from marshmallow import validate, fields

###############################################################################
# Land cover class, legend, and legend nesting schemas

@dataclass(frozen=True)
class LCClass:
    code: int
    name_short: str = field(metadata={"validate": validate.Length(max=15)})
    name_long: Optional[str] = field(default=None, metadata={"validate": validate.Length(max=50)})
    description: Optional[str] = field(default=None)

    class Meta:
        ordered = True

@dataclass
class LCLegend:
    name: str
    key: List[LCClass] = field(default_factory=list)

    #TODO: validate that all class codes are unique

    def __post_init__(self):
        self.class2code = {o: o.code for o in self.key}
        self.code2class = {o.code: o for o in self.key}

    class Meta:
        ordered = True


# Defines how a more detailed land cover legend nests within a higher-level 
# legend
@dataclass
class LCLegendNesting:
    parent: LCLegend
    child: LCLegend
    nesting: dict = field(default_factory=dict)

    # TODO: Add validation functions ensuring that:
    #   - each of the classes in parent and child are represented within the 
    #   nesting list
    #   - that no classes are in nesting list that aren't in parent and child

    class Meta:
        ordered = True

@dataclass
class LCTransMeaning:
    initial: LCClass
    final: LCClass
    meaning: str = field(metadata={'validate': validate.OneOf(["degradation", "stable", "improvement"])})

    class Meta:
        ordered = True

# Defines what each possible land cover transition means in terms of 
# degradation, so one of degraded, stable, or improved
@dataclass
class LCTransMatrix:
    legend: LCLegend
    transitions: List[LCTransMeaning] = field(default_factory=list)
    # TODO: Add validation functions ensuring that:
    #   - every possible transition given the legend is present in the 
    #   transitions list
    #   - that no transitions are in the transitions list that aren't possible 
    #   given the chosen legend

    class Meta:
        ordered = True

# ###############################################################################
# @dataclass
# class LCSummary:
#     legend: fields.Nested(LCLegend)
#     # Can exclude the "child" legend from the nesting field that is the same as 
#     # the overall legend for the LCSummary
#     nesting: fields.Nested(LCLegendNesting(exclude='child'))
#     # Can exclude the legend from the transition matrix field as it is the same 
#     # as the overall legend for the LCSummary
#     transition_matrix: fields.Nested(LCTransMatrix, exclude='legend')
#
#    class Meta:
#        ordered = True


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
    unit: str = field(metadata={'validate': validate.OneOf(["m", "ha", "km sq"])})
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
class TrendsEarthVersion:
    version: str
    revision: str
    release_date: str

    class Meta:
        ordered = True

@dataclass
class ReportMetadata:
    title: str
    date: datetime.datetime
    trends_earth_version: TrendsEarthVersion

    class Meta:
        ordered = True

@dataclass
class SDGReport:
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
    legend_nesting: LCLegendNesting
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
class TrendsEarthSummary:
    metadata: ReportMetadata
    sdg: SDGReport
    productivity: ProductivityReport
    land_cover: LandCoverReport
    soil_organic_carbon: SoilOrganicCarbonReport

    # TODO: Add land cover definitions

    # TODO: Add datasets needed for reporting (band number and filename)

    class Meta:
        ordered = True

