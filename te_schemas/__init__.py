import logging

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


class SchemaBase:
    """Base class for te_schemas schemas"""

    def validate(self):
        """Validate this instance (for example after making changes)"""
        data, errors = self.Schema().dump(self)
        self.Schema().validate(data)

    def dump(self):
        """Serialize to Python datatypes"""
        return self.__class__.Schema().dump(self)

    def dumps(self):
        """Serialize to json-formatted text"""
        return self.__class__.Schema().dumps(self)


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
