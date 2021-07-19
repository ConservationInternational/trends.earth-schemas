import math

from . import SchemaBase

from dataclasses import field
from typing import Dict, List, Optional

from marshmallow import validate, Schema
from marshmallow.exceptions import ValidationError
from marshmallow_dataclass import dataclass


###############################################################################
# Land cover class, legend, and legend nesting schemas


@dataclass(frozen=True)
class LCClass(SchemaBase):
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
class LCLegend(SchemaBase):
    name: str
    key: List[LCClass] = field(default_factory=list)

    def __post_init__(self):
        # Check all class codes are unique
        codes = [c.code for c in self.key]
        if not len(set(codes)) == len(codes):
            raise ValidationError('Duplicate LCClass code found in legend {}'.format(self.name))

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
class LCLegendNesting(SchemaBase):
    parent: LCLegend
    child: LCLegend
    # nesting is a dict where the keys are the parent classes, and the items
    # are the child classes
    nesting: Dict[int, List[int]] = field(default_factory=dict)

    class Meta:
        ordered = True

    def __post_init__(self):
        # Get all parent and child codes listed in nesting
        nesting_parent_codes = self.nesting.keys()
        # Note the below is to avoid having a list of lists of child codes 
        # given the structure the "items" method returns them in
        nesting_child_codes = [i for key,value in self.nesting.items() for i in value]

        # Sort the two nesting class lists by code before comparison with 
        # legend class lists
        nesting_parent_codes = sorted(nesting_parent_codes)
        nesting_child_codes = sorted(nesting_child_codes)

        if not len(set(nesting_parent_codes)) == len(nesting_parent_codes):
            raise ValidationError('Duplicates detected in parent codes listed '
                                  'in nesting - each parent must be listed '
                                  'once and only once')
        if not len(set(nesting_child_codes)) == len(nesting_child_codes):
            raise ValidationError('Duplicates detected in child codes listed '
                                  'in nesting - each child must be listed '
                                  'once and only once')

        # Check that nesting_parent_codes list is an is exact match of parent 
        # legend class list, and likewise for child
        if not (self.parent.codes() == nesting_parent_codes):
            raise ValidationError("Codes listed in nesting dictionary don't "
                                  "match parent key")
        if not (self.child.codes() == nesting_child_codes):
            raise ValidationError("Codes listed in nesting dictionary don't "
                                  "match child key")

    def parentClassForChild(self, c):
        parent_code = [key for key, values in self.nesting.items()
                       if c.code in values]
        if len(parent_code) == 0:
            raise KeyError
        else:
            return self.parent.classByCode(parent_code[0])

    def get_list(self):
        '''Return the nesting in format needed for GEE'''
        out = [[], []]
        # keys are parents, values are child (remapping from child to parent in
        # GEE)
        for key, values in self.nesting.items():
            out[0].extend(values)
            out[1].extend([key] * len(values))
        return out


@dataclass
class LCTransMeaning(SchemaBase):
    initial: LCClass
    final: LCClass
    meaning: str = field(metadata={'validate':
                                   validate.OneOf(["degradation",
                                                   "stable",
                                                   "improvement"])})

    class Meta:
        ordered = True

    def get_meaning_int(self):
        meaning_key = {'degradation': -1,
                       'stable': 0,
                       'improvement': 1}
        return meaning_key[self.meaning]


@dataclass
class LCTransMatrix(SchemaBase):
    '''Define meaning of each possible land cover transition'''
    legend: LCLegend
    transitions: List[LCTransMeaning] = field(default_factory=list)

    class Meta:
        ordered = True

    def __post_init__(self):
        '''Ensure each transition is represented once and only once'''
        for c_final in self.legend.key:
            for c_initial in self.legend.key:
                trans = [t for t in self.transitions if
                        (t.initial == c_initial) and
                        (t.final == c_final)]
                if len(trans) == 0:
                    raise ValidationError("Meaning of transition from {} to "
                                          "{} is undefined".format(c_initial, c_final))
                if len(trans) > 1:
                    raise ValidationError("Multiple definitions found for "
                                          "transition from {} to {} - each "
                                          "transition must have only one "
                                          "meaning".format(c_initial, c_final))

        if (len(self.transitions) != len(self.legend.key)**2):
            raise ValidationError("Transitions list length does not match "
                                  "expected length based on legend")

    def meaningByTransition(self, initial, final):
        '''Get meaning for a particular transition'''
        out = [m.meaning for m in self.transitions if (m.initial == initial)
               and (m.final == final)][0]
        if out == []:
            return KeyError
        else:
            return out

    def get_multiplier(self):
        '''Return multiplier for transition calculations

        Used to figure out what number to multiply initial codes by so that, 
        when added to the final class code,  the result is the same as if the 
        class codes were added as strings. For example: if the initial class 
        code were 7, and, the  final class code were 5, the transition would be 
        coded as 75)'''
        return math.ceil(max([c.code for c in self.legend.key]) / 10) * 10

    def get_list(self):
        '''Get transition matrix, in GEE format'''
        out = [[], []]
        for c_final in self.legend.key:
            for c_initial in self.legend.key:
                out[0].append(c_initial.code * self.get_multiplier() + c_final.code)
                trans = [t for t in self.transitions if
                         (t.initial == c_initial) and
                         (t.final == c_final)][0]
                out[1].append(trans.get_meaning_int())
        return out

    def get_persistence_list(self):
        '''Get transition matrix to remap persistence classes, in GEE format

        Remap persistence class codes (11, 22), etc., so they are sequential 
        (1, 2, etc.). This makes it easier to assign a clear color ramp in 
        QGIS.'''
        out = [[], []]
        for c_final in self.legend.key:
            for c_initial in self.legend.key:
                original_code = c_initial.code * self.get_multiplier() + c_final.code
                out[0].append(original_code)
                if c_final.code == c_initial.code:
                    out[1].append(c_initial.code)
                else:
                    out[1].append(original_code)
        return out
