import logging
import re

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


class SchemaBase:
    """Base class for te_schemas schemas"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._normalize_schema_attribute()

    @classmethod
    def _build_schema_factory(cls):
        from marshmallow_dataclass import class_schema

        schema_class = class_schema(cls)

        def _factory():
            return schema_class()

        return staticmethod(_factory)

    @classmethod
    def _normalize_schema_attribute(cls):
        # Keep behavior stable even if the marshmallow dataclass decorator failed
        # to attach a usable Schema attribute (Marshmallow >=4)
        schema_attr = getattr(cls, "Schema", None)

        if schema_attr is None:
            cls.Schema = cls._build_schema_factory()
            return

        try:
            candidate = schema_attr()
        except TypeError:
            candidate = None
        except Exception:  # pragma: no cover - defensive guard
            candidate = None

        if candidate is not None and hasattr(candidate, "load"):
            cls.Schema = staticmethod(lambda attr=schema_attr: attr())
            return

        if hasattr(schema_attr, "load"):
            instance = schema_attr
            cls.Schema = staticmethod(lambda inst=instance: inst)
            return

        cls.Schema = cls._build_schema_factory()

    @classmethod
    def schema(cls):
        factory = getattr(cls, "Schema", None)
        if factory is None:
            cls._normalize_schema_attribute()
            factory = getattr(cls, "Schema")
        return factory()

    def validate(self):
        """Validate this instance (for example after making changes)"""
        schema = self.__class__.schema()
        data = schema.dump(self)
        schema.validate(data)

    def dump(self):
        """Serialize to Python datatypes"""
        return self.__class__.schema().dump(self)

    def dumps(self):
        """Serialize to json-formatted text"""
        return self.__class__.schema().dumps(self)


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
