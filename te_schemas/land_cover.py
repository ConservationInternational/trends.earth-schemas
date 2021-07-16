from dataclasses import field
from typing import Dict, List, Optional

from marshmallow_dataclass import dataclass
from marshmallow import validate

###############################################################################
# Land cover class, legend, and legend nesting schemas


@dataclass(frozen=True)
class LCClass:
    code: int
    name_short: str = field(metadata={"validate": validate.Length(max=15)}, 
                            default=None)
    name_long: str = field(default=None,
                           metadata={"validate": validate.Length(max=90)})
    description: Optional[str] = field(default=None)
    color: Optional[str] = field(default=None,
                                 metadata={'validate': validate.Regexp('^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$')})

    class Meta:
        ordered = True


@dataclass
class LCLegend:
    name: str
    key: List[LCClass] = field(default_factory=list)

    def __post_init__(self):
        # Check all class codes are unique
        codes = [c.code for c in self.key]
        if not len(set(codes)) == len(codes):
            raise KeyError('Duplicate LCClass code found in legend {}'.format(self.name))

        # Sort key by class codes
        self.key = sorted(self.key, key=lambda c: c.code)

    def codes(self):
        return [c.code for c in self.key]

    def classByCode(self, code):
        out = [c for c in self.key if c.code == code][0]
        if out == []:
            raise KeyError('No LCClass found for code "{}"'.format(code))
        else:
            return out

    def classByNameLong(self, name_long):
        out = [c for c in self.key if c.name_long == name_long][0]
        if out == []:
            return KeyError
        else:
            return out

    def orderByCode(self):
        return LCLegend(name=self.name,
                        key=sorted(list(self.key),
                                   key=lambda k: k.code))

    class Meta:
        ordered = True


# Defines how a more detailed land cover legend nests within a higher-level 
# legend
@dataclass
class LCLegendNesting:
    parent: LCLegend
    child: LCLegend
    nesting: Dict[int, List[int]] = field(default_factory=dict)

    class Meta:
        ordered = True

    def __post_init__(self):
        # Get all parent and child classes listed in nesting
        nesting_parent_classes = self.nesting.keys()
        # Note the below is to avoid having a list of lists of child classes 
        # given the structure the "items" method returns them in
        nesting_child_classes = [i for key,value in self.nesting.items() for i in value]

        # Sort the two nesting class lists by code before comparison with 
        # legend class lists
        nesting_parent_classes = sorted(nesting_parent_classes, key=lambda c: c.code)
        nesting_child_classes = sorted(nesting_child_classes, key=lambda c: c.code)

        if not len(set(nesting_parent_classes)) == len(nesting_parent_classes):
            raise KeyError('Duplicates detected in parent classes listed in nesting - each parent must be listed once and only once'.format(self.name))
        if not len(set(nesting_child_classes)) == len(nesting_child_classes):
            raise KeyError('Duplicates detected in child classes listed in nesting - each child must be listed once and only once'.format(self.name))

        # Check that nesting_parent_classes list is an is exact match of parent 
        # legend class list, and likewise for child
        if not (self.parent.key == nesting_parent_classes):
            raise KeyError("Classes listed in nesting dictionary don't match parent key")
        if not (self.child.key == nesting_child_classes):
            raise KeyError("Classes listed in nesting dictionary don't match child key")

    def parentClassForChild(self, c):
        parent_code = [key for key, values in self.nesting.items() if c.code in values]
        if len(parent_code) == 0:
            raise KeyError
        else:
            return self.parent.classByCode(parent_code[0])


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

    def meaningByTransition(self, initial, final):
        out = [m.meaning for m in self.transitions if (m.initial == initial) and (m.final == final)][0]
        if out == []:
            return KeyError
        else:
            return out

    def get_matrix(self, order):
        pass
        # Return a transition matrix with rows and columns ordered according to 
        # the list of classes given in "order"
        ##for c in order:
