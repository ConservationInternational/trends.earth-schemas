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
    color: Optional[str] = field(default=None, metadata={'validate': validate.Regexp('^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$')})

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

    def codes(self):
        return [c.code for c in self.key]

    def classByCode(self, code):
        out = [c for c in self.key if c.code == code][0]
        if out == []:
            return KeyError
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
                        key=sorted(list(self.key), key = lambda k: k.code))

    class Meta:
        ordered = True


# Defines how a more detailed land cover legend nests within a higher-level 
# legend
@dataclass
class LCLegendNesting:
    parent: LCLegend
    child: LCLegend
    nesting: Dict[int, List[int]] = field(default_factory=dict)

    # TODO: Add validation functions ensuring that:
    #   - each of the classes in parent and child are represented within the 
    #   nesting list
    #   - each of the classes in child are nested in one and only 1 parent 
    #   class
    #   - that no classes are in nesting list that aren't in parent and child

    class Meta:
        ordered = True

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
