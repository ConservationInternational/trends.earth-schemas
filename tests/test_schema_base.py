"""Tests for SchemaBase compatibility helpers."""

from __future__ import annotations

import marshmallow
import marshmallow_dataclass

from te_schemas import SchemaBase


def _make_schema_class():
    @marshmallow_dataclass.dataclass
    class ExampleSchema(SchemaBase):
        value: int

    return ExampleSchema


def test_schema_base_schema_is_callable():
    klass = _make_schema_class()
    schema = klass.Schema()

    loaded = schema.load({"value": 7})

    assert isinstance(schema, marshmallow.Schema)
    assert isinstance(loaded, klass)
    assert loaded.value == 7


def test_schema_base_recovers_invalid_schema_attribute():
    klass = _make_schema_class()
    klass.Schema = "broken"  # type: ignore[assignment]

    klass._normalize_schema_attribute()

    schema = klass.Schema()
    loaded = schema.load({"value": 4})

    assert isinstance(schema, marshmallow.Schema)
    assert isinstance(loaded, klass)
    assert loaded.value == 4


def test_schema_base_wraps_schema_instances():
    klass = _make_schema_class()
    schema_instance = klass.Schema()

    klass.Schema = schema_instance  # type: ignore[assignment]

    klass._normalize_schema_attribute()

    schema_again = klass.Schema()

    assert schema_again is schema_instance

    loaded = schema_again.load({"value": 9})
    assert isinstance(loaded, klass)
    assert loaded.value == 9
