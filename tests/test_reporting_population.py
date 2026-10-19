import json

import pytest
from marshmallow import ValidationError
from te_schemas.reporting import Population, PopulationList


@pytest.mark.parametrize("value", [0, 0.25, 40000.75, 123456789.125])
@pytest.mark.parametrize(
    "pop_type", ["Total population", "Male population", "Female population"]
)
def test_population_json_preserves_counts_and_fractions(value, pop_type):
    population = PopulationList(
        "Population by class", [Population("Degraded", value, pop_type)]
    )
    schema = PopulationList.Schema()
    serialized = schema.dumps(population)
    assert json.loads(serialized)["values"][0]["population"] == value
    assert schema.loads(serialized) == population


@pytest.mark.parametrize("value", [-0.25, float("nan"), float("inf")])
def test_population_rejects_invalid_counts(value):
    with pytest.raises(ValidationError):
        Population.Schema().load(
            {"name": "Degraded", "population": value, "type": "Total population"}
        )
