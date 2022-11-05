import json
import os
from pathlib import Path

import pytest

from te_schemas import land_cover


def _get_json(file):
    test_dir = Path(os.path.abspath(__file__)).parent
    with open(test_dir / "data" / file) as f:
        return json.load(f)


def test_legend_nesting():
    land_cover.LCLegendNesting.Schema().load(
        _get_json("land_cover-nesting-unccd_esa.json")
    )

    with pytest.raises(Exception):
        # Below is wrong type
        land_cover.LCLegendNesting.Schema().load(
            _get_json("land_cover-legend-mapbiomas.json")
        )


def test_deg_matrix():
    land_cover.LCTransitionDefinitionDeg.Schema().load(
        _get_json("land_cover-transition_matrix-unccd.json")
    )
