from dataclasses import field
from typing import List, Optional

from marshmallow_dataclass import dataclass
from marshmallow import validate, fields

###############################################################################
# Land cover class, legend, and legend nesting schemas

@dataclass(frozen=True)
class LCClass:
    name_short: str = field(metadata={"validate": validate.Length(max=15)})
    name_long: str = field(metadata={"validate": validate.Length(max=50)})
    description: str
    code: int

@dataclass
class LCLegend:
    name: str
    key: List[LCClass] = field(default_factory=list)

    #TODO: validate that all class codes are unique

    def __post_init__(self):
        self.class2code = {o: o.code for o in self.key}
        self.code2class = {o.code: o for o in self.key}

# Defines how one or more child classes nests within a parent class
@dataclass
class LCClassNesting:
    parent: LCClass
    child: List[LCClass] = field(default_factory=list)

# Defines how a more detailed land cover legend nests within a higher-level 
# legend
@dataclass
class LCLegendNesting:
    parent: LCLegend
    child: LCLegend
    nesting: List[LCClassNesting] = field(default_factory=list)

    # TODO: Add validation functions ensuring that:
    #   - each of the classes in parent and child are represented within the 
    #   nesting list
    #   - that no classes are in nesting list that aren't in parent and child

@dataclass
class LCTransMeaning:
    initial: LCClass
    final: LCClass
    meaning: str = field(metadata={'validate': validate.OneOf(["degradation", "stable", "improvement"])})

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
# # Classes to contain all information for UNCCD reporting
# @dataclass
# class UNCCDReporting:
#     ###################
#     # SDG
#     
#     # proportion of land that is degraded
#     
#     # filename for hotspots geojson
#     # filename for brightspots geojson
#    
#     ###################
#     # Land cover
#     land_cover: fields.Nested(LCSummary)
#
#     # National cover statistics for each year of available data
#     # Degraded area statistics
#
