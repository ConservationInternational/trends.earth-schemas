from __future__ import annotations

import math
from dataclasses import field, fields
from typing import Any, Dict, List, Optional, Tuple

from marshmallow import validate, validates_schema
from marshmallow.exceptions import ValidationError
from marshmallow_dataclass import dataclass

from . import SchemaBase

###############################################################################
# Land cover class, legend, and legend nesting schemas


@dataclass
class LCClass(SchemaBase):
    code: int
    name_short: str = field(
        metadata={"validate": validate.Length(max=20)}, default=None
    )
    name_long: str = field(
        default=None, metadata={"validate": validate.Length(max=120)}
    )
    description: Optional[str] = field(default=None)
    color: Optional[str] = field(
        default=None,
        metadata={"validate": validate.Regexp("^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$")},
    )

    def update(self, other: "LCClass"):
        """
        Update this object with attribute values from another LCClass object.
        Does not update 'code' since its assumed to be the unique identifier.
        """
        attrs = [f.name for f in fields(self)]
        for attr in attrs:
            if not hasattr(other, attr) or attr == "code":
                continue
            other_val = getattr(other, attr)
            self_val = getattr(self, attr)
            if self_val != other_val:
                object.__setattr__(self, attr, other_val)

    def get_name_short(self):
        if self.name_short and self.name_short != "":
            return self.name_short
        else:
            return self.name_long[0:20]

    def get_name(self):
        if self.name_short and self.name_short != "":
            return self.name_short
        else:
            return self.name_long

    def get_name_long(self):
        if self.name_long and self.name_long != "":
            return self.name_long
        else:
            return self.name_short

    def translate(self, translations):
        self.name_short = translations.get(self.name_short, self.name_short)
        self.name_long = translations.get(self.name_long, self.name_long)
        self.description = translations.get(self.description, self.description)

    def __eq__(self, other):
        if not isinstance(other, LCClass):
            return False
        elif (
            self.code == other.code
            and self.name_short == other.name_short
            and self.name_long == other.name_long
            and self.description == other.description
            and self.color == other.color
        ):
            return True
        else:
            return False


@dataclass
class LCLegend(SchemaBase):
    name: str
    key: List[LCClass] = field(default_factory=list)
    nodata: LCClass = field(default_factory=None)

    def __post_init__(self):
        # Check all class codes are unique
        codes = [c.code for c in self.key]

        if not len(set(codes)) == len(codes):
            raise ValidationError(f"Duplicate LCClass code found in legend {self.name}")

        # Sort key by class codes
        self.key = sorted(self.key, key=lambda c: c.code)

    def __eq__(self, other):
        if not isinstance(other, LCLegend):
            return False
        elif (
            self.name == other.name
            and sorted(self.key) == sorted(other.key)
            and self.nodata == other.nodata
        ):
            return True
        else:
            return False

    def _key_with_nodata(self):
        "soon to be deprecated"
        return self.key_with_nodata()

    def key_with_nodata(self):
        if self.nodata:
            return self.key + [self.nodata]
        else:
            return self.key

    def codes(self):
        return [c.code for c in self._key_with_nodata()]

    def classByCode(self, code):
        out = [c for c in self._key_with_nodata() if c.code == code]

        if out == []:
            raise KeyError('No LCClass found for code "{}"'.format(code))
        else:
            return out[0]

    def classByNameLong(self, name_long):
        out = [c for c in self._key_with_nodata() if c.name_long == name_long][0]

        if out == []:
            return KeyError
        else:
            return out

    def orderByCode(self):
        return LCLegend(
            name=self.name,
            key=sorted(list(self.key), key=lambda k: k.code),
            nodata=self.nodata,
        )

    def class_by_code(self, code: int) -> LCClass:
        # Legacy support. Previous implementation raises an exception.
        return self.class_by_attr("code", code)

    def class_index(self, lcc: LCClass) -> int:
        # Returns index (1-based) of class after ordering key by codes
        ordered_codes = sorted([c.code for c in self.key])
        return ordered_codes.index(lcc.code) + 1

    def contains_key(self, code: int) -> bool:
        # Checks if there is a class with the given 'code'.
        lcc = self.class_by_code(code)
        if lcc is None:
            return False

        return True

    def add_update_class(self, lcc: LCClass):
        """
        Checks if the given LCC exists, if True then it updates it else adds
        it to the 'key' collection.
        """
        key_lcc = self.class_by_code(lcc.code)

        if key_lcc is None:
            self.key.append(lcc)
        else:
            key_lcc.update(lcc)

    def remove_class(self, code: int) -> bool:
        """
        Removes the class with the given code from the 'key'
        collection.
        """
        if not self.contains_key(code):
            return False

        idxs = [i for i, lcc in enumerate(self.key) if lcc.code == code]
        rem_idx = idxs[0]
        _ = self.key.pop(rem_idx)

        return True

    def class_by_name_long(self, name_long: str) -> LCClass:
        # Returns a class matching the given name_long else None.
        return self.class_by_attr("name_long", name_long)

    def class_by_attr(self, attr_name, attr_val) -> LCClass:
        """
        Returns class in 'key' attribute by searching based on attribute
        name and corresponding value.
        """
        lcc = None
        try:
            matches = [
                c
                for c in self.key
                if c is not None and getattr(c, attr_name) == attr_val
            ]
            if len(matches) > 0:
                lcc = matches[0]
        except AttributeError as ae:
            raise ae

        return lcc

    def translate(self, translations):
        for c in self.key:
            c.translate(translations)
        self.nodata.translate(translations)

    def get_ramp_items(self):
        """
        Uses the values, color hex codes, and labels to return a list of style items in
        the format needed to generate a style for a layer within the QGIS Trends.Earth
        plugin
        """
        out = []
        for c in self._key_with_nodata():
            if c.name_long:
                name = c.name_long
            else:
                name = c.name_short
            out.append({"value": c.code, "label": name, "color": c.color})
        return out

    def get_transitions_ramp_items(self, translations={}):
        """
        Uses the values, color hex codes, and labels to return a list of style
        items for transtiions among classes in the format needed to generate
        a style for a layer within the QGIS Trends.Earth plugin
        """
        # TODO: Need to handle translations in this function
        out = [
            {
                "value": self.nodata.code,
                "label": translations.get("No data", "No data"),
                "color": self.nodata.color,
            },
            {
                "value": len(self.key),
                "label": translations.get("No change", "No change"),
                "color": "#ffffe0",
            },
        ]
        for c in self.key:
            if c.name_long:
                name = c.name_long
            else:
                name = c.name_short
            out.append(
                {
                    "value": self.class_index(c) * self.get_multiplier()
                    + len(self.key),
                    "label": f"{translations.get('Loss', f'{name} loss')}",
                    "color": c.color,
                }
            )
        return out

    def get_multiplier(self):
        """Return multiplier for transition calculations

        Used to figure out what number to multiply an initial class code by so that
        when added to a code for the class that a pixel transitions into, the result
        is the same as if the two codes were concatenated as strings.

        This function is retained for backwards-compatibility. The number
        of classes in a legend in the QGIS plugin is limited 38, and the codes used
        to represent classes in the transition layers are the position of each class
        in an ordered list of class codes. This ensures a multiplier greater than 100
        is never needed.
        """

        return 10 ** math.ceil(math.log10(len(self.key)))


# Defines how a more detailed land cover legend nests within a
# higher-level legend
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
        nesting_child_codes = [i for key, value in self.nesting.items() for i in value]

        # Sort the two nesting class lists by code before comparison with
        # legend class lists
        nesting_parent_codes = sorted(nesting_parent_codes)
        nesting_child_codes = sorted(nesting_child_codes)

        if not len(set(nesting_parent_codes)) == len(nesting_parent_codes):
            raise ValidationError(
                "Duplicates detected in parent codes listed "
                "in nesting - each parent must be listed "
                "once and only once. Parent codes: "
                f"{nesting_parent_codes}"
            )

        if not len(set(nesting_child_codes)) == len(nesting_child_codes):
            raise ValidationError(
                "Duplicates detected in child codes listed "
                "in nesting - each child must be listed "
                "once and only once. Child codes: "
                f"{nesting_child_codes}"
            )

        # Check that nesting_parent_codes list is an is exact match of parent
        # legend class list, and likewise for child

        if not (sorted(self.parent.codes()) == nesting_parent_codes):
            raise ValidationError(
                f"Codes listed in nesting dictionary {nesting_parent_codes} "
                f"don't match parent key {self.parent.codes()}"
            )

        if not (sorted(self.child.codes()) == nesting_child_codes):
            raise ValidationError(
                f"Codes listed in nesting dictionary {nesting_child_codes} "
                f"don't match child key {self.child.codes()}"
            )

    def update_parent(self, child, new_parent):
        # Remove the child class from the old parent
        old_parent = self.parentClassForChild(child)
        self.nesting[old_parent.code].remove(child.code)
        self.nesting[new_parent.code].append(child.code)

    def parentClassForChild(self, c):
        parent_code = [key for key, values in self.nesting.items() if c.code in values]

        if len(parent_code) == 0:
            raise KeyError
        else:
            return self.parent.classByCode(parent_code[0])

    def get_list(self):
        """Return the nesting in format needed for GEE"""
        out = [[], []]
        # keys are parents, values are child (remapping from child to parent in
        # GEE)

        for key, values in self.nesting.items():
            out[0].extend(values)
            out[1].extend([key] * len(values))

        return out

    def parent_for_child(self, c) -> LCClass:
        """
        Returns the parent for the given child. Varies from
        :ref:`parentClassForChild` in that it does not raise an error if
        there is no parent, but instead returns None.
        """
        parent_code = [key for key, values in self.nesting.items() if c.code in values]

        if len(parent_code) == 0:
            return None

        return self.parent.class_by_code(parent_code[0])

    def child_class(self, code: int) -> LCClass:
        """
        Gets a child with the given code, else None.
        """
        return self.child.class_by_code(code)

    def add_update_parent(self, parent_lcc: LCClass, children: Optional[List[LCClass]]):
        # Add new or update existing parent class with the given children.
        self.parent.add_update_class(parent_lcc)
        if children is not None and len(children) > 0:
            self.add_update_children(children, parent_lcc)

    def add_update_children(self, children: List[LCClass], parent_lcc: LCClass) -> bool:
        """
        Add children to the given parent. If parent does not exist it will
        return False.
        """
        if not self.parent.contains_key(parent_lcc.code):
            return False

        for c in children:
            child_nodata = self.child.nodata
            if not (child_nodata and c.code == child_nodata.code):
                ex_child = self.child_class(c.code)
                if ex_child is None:
                    self.child.add_update_class(c)

            parent = self.parent_for_child(c)
            if parent is not None:
                self.nesting[parent.code].remove(c.code)

            if parent_lcc.code not in self.nesting:
                self.nesting[parent_lcc.code] = []

            self.nesting[parent_lcc.code].append(c.code)

        return True

    def children_for_parent(self, parent_lcc: LCClass) -> List[LCClass]:
        """
        Get children for the given parent. Returns an empty list if the
        parent does not exist.
        """
        if parent_lcc.code not in self.nesting:
            return []

        child_codes = self.nesting[parent_lcc.code]
        children = []
        for cc in child_codes:
            child = self.child_class(cc)
            if child is not None:
                children.append(child)

        return children

    def orphan_children(self) -> List[LCClass]:
        """
        Returns a list of orphaned children i.e. without parents defined
        through nesting.
        """
        children = self.child.key

        return [c for c in children if self.parent_for_child(c) is None]

    def remove_parent_class(self, parent_lcc: LCClass) -> bool:
        """
        Removes parent and corresponding child references in nesting.
        """
        if not self.parent.contains_key(parent_lcc.code):
            return False

        self.parent.remove_class(parent_lcc.code)

        if parent_lcc.code in self.nesting:
            del self.nesting[parent_lcc.code]

        return True

    def nest(self, nesting) -> LCLegendNesting:
        """
        Given a nesting instance whose child class is the parent of this one, will nest
        this child class legend under the parent of that instance, and return a new
        nesting instance
        """

        if self.parent != nesting.child:
            raise Exception

        nesting = {}
        for lcc in nesting.key:
            current_parent_class = self.parentForChild(lcc)
            new_parent_class = nesting.parentForChild(current_parent_class)
            if lcc.code not in nesting:
                nesting[new_parent_class.code] = [lcc.code]
            else:
                nesting[new_parent_class.code].append(lcc.code)

        return LCLegendNesting(parent=nesting.parent, child=self.child, nesting=nesting)

    def translate(self, translations):
        self.parent.translate(translations)
        self.child.translate(translations)

    def get_multiplier(self):
        """Return multiplier for transition calculations

        Used to figure out what number to multiply an initial class code by so that
        when added to a code for the class that a pixel transitions into, the result
        is the same as if the two codes were concatenated as strings.

        This function is retained for backwards-compatibility. The number
        of classes in a legend in the QGIS plugin is limited 38, and the codes used
        to represent classes in the transition layers are the position of each class
        in an ordered list of class codes. This ensures a multiplier greater than 100
        is never needed.
        """

        return 10 ** math.ceil(
            math.log10(max([len(self.child.key), len(self.parent.key)]))
        )


###############################################################################
# Base classes for transition matrices to be used in defining meaning of land
# cover transitions in terms of degraded/stable/improvement, soil organic
# carbon change factors, etc.
@dataclass
class LCTransitionMatrixBase(SchemaBase):
    """Base class to define meaning of land cover transitions

    Base class used for transition matrices defining meaning of land
    cover transitions in terms of degraded/stable/improvement, soil organic
    carbon change factors, etc."""

    transitions: list
    name: str

    def meaningByTransition(self, initial, final):
        """Get meaning for a particular transition"""
        out = [
            m.meaning
            for m in self.transitions
            if (m.initial == initial) and (m.final == final)
        ][0]

        if out == []:
            return KeyError
        else:
            return out

    def meaning_by_transition(
        self, initial: LCClass, final: LCClass
    ) -> "LCTransitionMeaningDeg":
        """
        Returns the meanings which contain the given land cover classes for
        initial and final respectively. Differs from
        :ref:`meaningByTransition` as it uses the code for comparison and
        will not raise an error but will return None if there is no match.
        """
        matches = [
            m
            for m in self.transitions
            if (m.initial.code == initial.code) and (m.final.code == final.code)
        ]
        if len(matches) == 0:
            return None

        return matches[0]

    def meanings_by_class(self, lcc: LCClass) -> List["LCTransitionMeaningDeg"]:
        """
        Returns the meanings which contain the given land cover class in the
        'initial' and/or 'final' attributes.
        """
        return [
            m
            for m in self.transitions
            if (m.initial.code == lcc.code) or (m.final.code == lcc.code)
        ]


def _validate_matrix(legend, transitions):
    for c_final in legend.key:
        for c_initial in legend.key:
            if legend.nodata in (c_initial, c_final):
                # Don't allow transitions to be defined when initial or final
                # class are nodata class
                raise ValidationError(
                    f"Meaning of transition from {c_initial} to {c_final} "
                    f"is defined, but nodata is {legend.nodata}. Transition "
                    "meanings are not allowed for transitions from or to "
                    "nodata class."
                )
            trans = [
                t
                for t in transitions
                if (t.initial == c_initial) and (t.final == c_final)
            ]

            if len(trans) == 0:
                raise ValidationError(
                    f"Meaning of transition from {c_initial} to {c_final} "
                    f"is undefined (nodata is {legend.nodata})."
                )

            if len(trans) > 1:
                raise ValidationError(
                    "Multiple definitions found for "
                    "transition from {} to {} - each "
                    "transition must have only one "
                    "meaning".format(c_initial, c_final)
                )

    if len(transitions) != len(legend.key) ** 2:
        raise ValidationError(
            "Transitions list length for {} does not match "
            "expected length based on legend"
        )


@dataclass
class LCTransitionDefinitionBase(SchemaBase):
    """Base class to define meaning of land cover transitions

    Can contain one more more definitions TransitionMatrixBase"""

    legend: LCLegend
    name: str
    definitions: Any

    @validates_schema
    def validate_transitions(self, data, **kwargs):
        """Ensure each transition is represented once and only once"""

        if isinstance(data["definitions"], dict):
            for key, m in data["definitions"]:
                _validate_matrix(data["legend"], m.transitions)
        elif isinstance(data["definitions"], LCTransitionMatrixBase):
            _validate_matrix(data["legend"], data["definitions"].transitions)
        else:
            raise ValidationError

        return data

    def get_list(self, key=None):
        """Get transition matrix, in GEE format"""

        if isinstance(self.definitions, dict):
            if key is None:
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
                out[0].append(
                    self.legend.class_index(c_initial) * self.legend.get_multiplier()
                    + self.legend.class_index(c_final)
                )
                trans = [
                    t
                    for t in m.transitions
                    if (t.initial == c_initial) and (t.final == c_final)
                ][0]
                out[1].append(trans.code())

        return out

    def get_persistence_list(self):
        """Get transition matrix to remap persistence classes, in GEE format

        Remap persistence class codes (11, 22), etc., so they are sequential
        (1, 2, etc.). This makes it easier to assign a clear color ramp in
        QGIS."""
        out = [[], []]

        for c_initial in self.legend.key:
            for c_final in self.legend.key:
                original_code = self.legend.class_index(
                    c_initial
                ) * self.legend.get_multiplier() + self.legend.class_index(c_final)
                out[0].append(original_code)

                if c_final.code == c_initial.code:
                    out[1].append(self.legend.class_index(c_initial))
                else:
                    out[1].append(original_code)

        return out

    def get_transition_integers_key(self):
        """
        Get key linking initial/final classes to their transition codes

        First keys are transition codes, values contain a dict of initial/final class
        """
        out = {}

        for c_initial in self.legend.key:
            for c_final in self.legend.key:
                out[
                    self.legend.class_index(c_initial) * self.legend.get_multiplier()
                    + self.legend.class_index(c_final)
                ] = {
                    "initial": c_initial.code,
                    "final": c_final.code,
                }

        return out

    def get_transition_initial_final_key(self):
        """
        Get key linking initial/final classes to their transition codes

        First keys are transition codes, values contain a dict of initial/final class
        """
        out = {}

        for c_initial in self.legend.key:
            for c_final in self.legend.key:
                if c_initial.code not in out:
                    out[c_initial.code] = {}
                out[c_initial.code][c_final.code] = self.legend.class_index(
                    c_initial
                ) * self.legend.get_multiplier() + self.legend.class_index(c_final)

        return out

    def get_definition(self, initial, final):
        return self.definitions.meaning_by_transition(initial, final)


@dataclass
class LCTransitionMeaning(SchemaBase):
    initial: LCClass
    final: LCClass
    meaning: Any  # Override with particular type when subclassed

    def contains_class(self, lcc: LCClass) -> Tuple[bool, list]:
        """
        Return False if the given class does not exist in the 'initial'
        and/or 'initial' attributes, else returns True together with the
        matching classes.
        """
        status = False
        classes = []
        if self.initial.code == lcc.code:
            status = True
            classes.append(self.initial)

        if self.final.code == lcc.code:
            if not status:
                status = True
            classes.append(self.final)

        return status, classes

    def update_class(self, lcc: LCClass):
        """
        Updates the LCClass objects in 'initial' or 'final' attributes if
        the given class exists in one or both of these attributes.
        """
        status, classes = self.contains_class(lcc)
        if not status:
            return

        for c in classes:
            c.update(lcc)

    def translate(self, translations):
        self.initial.translate(translations)
        self.final.translate(translations)


###############################################################################
# Land cover change transition definitions (degraded/stable/improvement)
@dataclass
class LCTransitionMeaningDeg(LCTransitionMeaning):
    meaning: str = field(
        metadata={"validate": validate.OneOf(["degradation", "stable", "improvement"])}
    )

    class Meta:
        ordered = True

    def code(self):
        meaning_key = {"degradation": -1, "stable": 0, "improvement": 1}

        return meaning_key[self.meaning]


@dataclass
class LCTransitionMatrixDeg(LCTransitionMatrixBase):
    transitions: List[LCTransitionMeaningDeg]

    def remove_meanings_by_class(self, lcc: LCClass) -> bool:
        """
        Remove LCTransitionMeaningDeg objects containing the given LCClass
        object. Returns True if at least one meaning was found.
        """
        i = 0
        status = False
        while i < len(self.transitions):
            meaning = self.transitions[i]
            if meaning.contains_class(lcc):
                _ = self.transitions.pop(i)
                if not status:
                    status = True
            else:
                i += 1

        return status

    def update_meaning_classes(self, lcc: LCClass):
        """
        Update LCClass 'initial' and 'final' attributes in meaning containing
        the given class.
        """
        for m in self.transitions:
            m.update_class(lcc)

    def translate(self, translations):
        for transition in self.transitions:
            transition.translate(translations)


@dataclass
class LCTransitionDefinitionDeg(LCTransitionDefinitionBase):
    """Define meaning of land cover transitions in terms of degradation"""

    definitions: LCTransitionMatrixDeg

    def add_update_class(self, lcc: LCClass, meaning_str=None):
        """
        Adds new or updates existing LCClass object to both the legend and
        definitions.
        """
        if meaning_str is None:
            meaning_str = "stable"

        self.legend.add_update_class(lcc)

        for init_lcc in self.legend.key:
            for final_lcc in self.legend.key:
                init_meaning = self.definitions.meaning_by_transition(
                    init_lcc, final_lcc
                )
                if init_meaning is None:
                    init_meaning = LCTransitionMeaningDeg(
                        init_lcc, final_lcc, meaning_str
                    )
                    self.definitions.transitions.append(init_meaning)

                final_meaning = self.definitions.meaning_by_transition(
                    final_lcc, init_lcc
                )
                if final_meaning is None:
                    final_meaning = LCTransitionMeaningDeg(
                        final_lcc, init_lcc, meaning_str
                    )
                    self.definitions.transitions.append(final_meaning)

        self.definitions.update_meaning_classes(lcc)

    def remove_class(self, lcc: LCClass) -> bool:
        """
        Remove references matching the given land cover class from the
        legend and definitions.
        """
        status = True

        if not self.legend.remove_class(lcc.code):
            status = False
        if not self.definitions.remove_meanings_by_class(lcc):
            status = False

        return status

    def translate(self, translations):
        self.definitions.translate(translations)
        self.legend.translate(translations)
