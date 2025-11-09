import json
import os
from pathlib import Path

import pytest
from marshmallow.exceptions import ValidationError

from te_schemas import land_cover


def _get_json(file):
    test_dir = Path(os.path.abspath(__file__)).parent
    with open(test_dir / "data" / file) as f:
        return json.load(f)


def _load_schema(dataclass_type, payload):
    schema = getattr(dataclass_type, "Schema")()
    return schema.load(payload)


def test_legend_nesting():
    _load_schema(
        land_cover.LCLegendNesting,
        _get_json("land_cover-nesting-unccd_esa.json"),
    )

    with pytest.raises(ValidationError):
        # Below is wrong type
        _load_schema(
            land_cover.LCLegendNesting, _get_json("land_cover-legend-mapbiomas.json")
        )


def test_deg_matrix():
    _load_schema(
        land_cover.LCTransitionDefinitionDeg,
        _get_json("land_cover-transition_matrix-unccd.json"),
    )


def test_schema_base_validate_raises_on_invalid_data():
    invalid_class = land_cover.LCClass(code=1, name_short="Test", color="not-a-hex")

    with pytest.raises(ValidationError):
        invalid_class.validate()
