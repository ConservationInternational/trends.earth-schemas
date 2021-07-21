import math

from . import SchemaBase

from dataclasses import field
from typing import Dict, List, Optional, Any

from marshmallow import validate, Schema, post_load, pre_load, validates_schema
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


# Defines how a more detailed land cover legend nests within a higher-level 
# legend
@dataclass
class LCLegendNesting(SchemaBase):
    parent: LCLegend
    child: LCLegend
    # nesting is a dict where the keys are the parent classes, and the items
    # are the child classes
    nesting: Dict[int, List[int]] = field(default_factory=dict)

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


###############################################################################
# Base classes for transition matrices to be used in defining meaning of land 
# cover transitions in terms of degraded/stable/improvement, soil organic 
# carbon change factors, etc.
@dataclass
class LCTransitionMatrixBase(SchemaBase):
    '''Base class to define meaning of land cover transitions

    Base class used for transition matrices defining meaning of land 
    cover transitions in terms of degraded/stable/improvement, soil organic 
    carbon change factors, etc.'''

    transitions: list
    name: str

    def meaningByTransition(self, initial, final):
        '''Get meaning for a particular transition'''
        out = [m.meaning for m in self.transitions if (m.initial == initial)
               and (m.final == final)][0]
        if out == []:
            return KeyError
        else:
            return out


def validate_matrix(legend, transitions):
    for c_final in legend.key:
        for c_initial in legend.key:
            trans = [t for t in transitions if
                    (t.initial == c_initial) and
                    (t.final == c_final)]
            if len(trans) == 0:
                raise ValidationError("Meaning of transition from {} to "
                                      "{} is undefined for {}".format(c_initial, c_final, transitions))
            if len(trans) > 1:
                raise ValidationError("Multiple definitions found for "
                                      "transition from {} to {} - each "
                                      "transition must have only one "
                                      "meaning".format(c_initial, c_final))

    if (len(transitions) != len(legend.key)**2):
        raise ValidationError("Transitions list length for {} does not match "
                              "expected length based on legend")


@dataclass
class LCTransitionDefinitionBase(SchemaBase):
    '''Base class to define meaning of land cover transitions

    Can contain one more more definitions TransitionMatrixBase'''

    legend: LCLegend
    name: str
    definitions: Any

    @validates_schema
    def validate_transitions(self, data, **kwargs):
        '''Ensure each transition is represented once and only once'''
        if isinstance(data['definitions'], dict):
            for key, m in data['definitions']:
                validate_matrix(data['legend'], m.transitions)
        elif isinstance(data['definitions'], LCTransitionMatrixBase):
                validate_matrix(data['legend'], data['definitions'].transitions)
        else:
            raise ValidationError
        return data

    def get_list(self, key=None):
        '''Get transition matrix, in GEE format'''
        if isinstance(self.definitions, dict):
            if key == None:
                raise Exception
            else:
                m = self.definitions[key]
        elif isinstance(self.definitions, LCTransitionMatrixBase):
            m = self.definitions
        else:
            raise Exception
        out = [[], []]
        for c_final in self.legend.key:
            for c_initial in self.legend.key:
                out[0].append(c_initial.code * self.get_multiplier() + c_final.code)
                trans = [t for t in m.transitions if
                         (t.initial == c_initial) and
                         (t.final == c_final)][0]
                out[1].append(trans.code())
        return out

    def get_persistence_list(self):
        '''Get transition matrix to remap persistence classes, in GEE format

        Remap persistence class codes (11, 22), etc., so they are sequential 
        (1, 2, etc.). This makes it easier to assign a clear color ramp in 
        QGIS.'''
        out = [[], []]
        for c_initial in self.legend.key:
            for c_final in self.legend.key:
                original_code = c_initial.code * self.get_multiplier() + c_final.code
                out[0].append(original_code)
                if c_final.code == c_initial.code:
                    out[1].append(c_initial.code)
                else:
                    out[1].append(original_code)
        return out

    def get_multiplier(self):
        '''Return multiplier for transition calculations

        Used to figure out what number to multiply initial codes by so that, 
        when added to the final class code,  the result is the same as if the 
        class codes were added as strings. For example: if the initial class 
        code were 7, and, the  final class code were 5, the transition would be 
        coded as 75)'''
        return math.ceil(max([c.code for c in self.legend.key]) / 10) * 10


@dataclass
class LCTransitionMeaning(SchemaBase):
    initial: LCClass
    final: LCClass
    meaning: Any  # Override with particular type when subclassed


###############################################################################
# Land cover change transition definitions (degraded/stable/improvement)
@dataclass
class LCTransitionMeaningDeg(LCTransitionMeaning):
    meaning: str = field(metadata={'validate':
                                   validate.OneOf(["degradation",
                                                   "stable",
                                                   "improvement"])})

    class Meta:
        ordered = True

    def code(self):
        meaning_key = {'degradation': -1,
                       'stable': 0,
                       'improvement': 1}
        return meaning_key[self.meaning]


@dataclass
class LCTransitionMatrixDeg(LCTransitionMatrixBase):
    transitions: List[LCTransitionMeaningDeg]


@dataclass
class LCTransitionDefinitionDeg(LCTransitionDefinitionBase):
    '''Define meaning of land cover transitions in terms of degradation'''
    definitions: LCTransitionMatrixDeg
