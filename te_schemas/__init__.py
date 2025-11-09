import logging
import re

from typing import Any, Type, TypeVar

import marshmallow_dataclass
from marshmallow import Schema as MarshmallowSchema
from marshmallow.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Import version information
try:
    from te_schemas._version import __version__, __git_sha__, __git_date__
except ImportError:
    __version__ = "unknown"
    __git_sha__ = "unknown"
    __git_date__ = "unknown"
    logging.warning(
        "te_schemas version could not be determined. "
        "If you're running from source, please run 'invoke set-version' first. "
        "If you're running from a package, this may indicate a packaging issue."
    )

# Backward compatibility attributes
__version_major__ = re.sub(r"([0-9]+)(\.[0-9]+)+.*$", r"\g<1>", __version__)
__release_date__ = __git_date__  # Use git date as release date


SchemaBaseT = TypeVar("SchemaBaseT", bound="SchemaBase")


def _ensure_schema_cls(cls: Type[Any]) -> Type[MarshmallowSchema]:
    schema_attr = getattr(cls, "Schema", None)
    if not callable(schema_attr):
        schema_attr = marshmallow_dataclass.class_schema(cls)
        setattr(cls, "Schema", schema_attr)
    return schema_attr  # type: ignore[return-value]


def schema_for(cls: Type[Any]) -> MarshmallowSchema:
    """Return a marshmallow schema instance for the given dataclass."""
    schema_cls = _ensure_schema_cls(cls)
    return schema_cls()


class SchemaBase:
    """Base class for te_schemas schemas"""

    @classmethod
    def schema(cls: Type[SchemaBaseT]) -> MarshmallowSchema:
        """Return a new marshmallow schema instance for this dataclass."""
        schema_cls = _ensure_schema_cls(cls)
        return schema_cls()

    def _schema(self) -> MarshmallowSchema:
        """Return a new marshmallow schema instance for this dataclass."""
        return self.__class__.schema()

    def validate(self):
        """Validate this instance (for example after making changes)"""
        schema = self._schema()
        data = schema.dump(self)
        errors = schema.validate(data)  # type: ignore[arg-type]
        if errors:
            raise ValidationError(errors)

    def dump(self):
        """Serialize to Python datatypes"""
        return self._schema().dump(self)

    def dumps(self):
        """Serialize to json-formatted text"""
        return self._schema().dumps(self)


def validate_matrix(legend, transitions):
    for c_final in legend.key:
        for c_initial in legend.key:
            trans = [
                t
                for t in transitions
                if (t["initial"] == c_initial) and (t["final"] == c_final)
            ]
            if len(trans) == 0:
                raise ValidationError(
                    "Meaning of transition from {} to {} is undefined for {}".format(
                        c_initial, c_final, transitions
                    )
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
