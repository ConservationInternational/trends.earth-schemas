"""Generic analysis results schemas for non-raster job outputs.

This module provides extensible result types for jobs that produce
structured data (summaries, per-entity records, time-series) rather
than raster imagery.  They slot into the existing ``ResultsField``
dispatch in :mod:`te_schemas.jobs` via the ``type`` discriminator.

Example
-------
An avoided-emissions job would produce::

    AnalysisResults(
        name="Avoided emissions",
        analysis_type="avoided_emissions",
        summary={
            "n_sites": 42,
            "total_emissions_avoided_mgco2e": 12345.6,
            "total_forest_loss_avoided_ha": 78.9,
            "total_area_ha": 5000.0,
        },
        records=[
            AnalysisRecord(
                entity_id="SITE_001",
                entity_name="Alto Mayo",
                period_start=2001,
                period_end=2020,
                values={
                    "forest_loss_avoided_ha": 12.3,
                    "emissions_avoided_mgco2e": 456.7,
                    "area_ha": 500.0,
                },
            ),
        ],
        time_series=[
            AnalysisTimeStep(
                entity_id="SITE_001",
                year=2015,
                values={
                    "forest_loss_avoided_ha": 1.5,
                    "emissions_avoided_mgco2e": 50.2,
                },
            ),
        ],
    )
"""

from __future__ import annotations

import dataclasses
import typing

import marshmallow
import marshmallow_dataclass
from marshmallow import validate

from te_schemas import SchemaBase
from te_schemas.results import ResultType

# ---------------------------------------------------------------------------
# Generic record and time-step containers
# ---------------------------------------------------------------------------


@marshmallow_dataclass.dataclass
class AnalysisTimeStep(SchemaBase):
    """A single time-step observation for one entity.

    Attributes
    ----------
    entity_id : str
        Identifier of the entity (site, region, pixel group, …).
    year : int
        The year this observation covers.
    values : dict
        Metric name → numeric value mapping.  Contents are analysis-specific.
    entity_name : str, optional
        Human-readable name for the entity.
    metadata : dict, optional
        Arbitrary per-observation metadata (e.g. ``n_matched_pixels``).
        Defaults to ``None``; callers should treat ``None`` as empty.
    """

    entity_id: str
    year: int
    values: dict
    entity_name: typing.Optional[str] = None
    metadata: typing.Optional[dict] = None


@marshmallow_dataclass.dataclass
class AnalysisRecord(SchemaBase):
    """Aggregated result for a single entity across its full analysis period.

    Attributes
    ----------
    entity_id : str
        Identifier of the entity.
    values : dict
        Metric name → numeric value mapping.  Contents are analysis-specific.
    entity_name : str, optional
        Human-readable name.
    period_start : int, optional
        First year of the analysis period for this entity.
    period_end : int, optional
        Last year of the analysis period for this entity.
    metadata : dict, optional
        Arbitrary per-entity metadata.
        Defaults to ``None``; callers should treat ``None`` as empty.
    """

    entity_id: str
    values: dict
    entity_name: typing.Optional[str] = None
    period_start: typing.Optional[int] = None
    period_end: typing.Optional[int] = None
    metadata: typing.Optional[dict] = None


# ---------------------------------------------------------------------------
# Top-level result container
# ---------------------------------------------------------------------------


@marshmallow_dataclass.dataclass
class AnalysisResults(SchemaBase):
    """Generic result container for non-raster analysis jobs.

    This schema is designed to be a flexible envelope: the ``summary`` dict
    holds global aggregates, ``records`` holds per-entity totals, and
    ``time_series`` holds per-entity-per-year observations.  All three use
    free-form dicts for the actual metric values so that the schema itself
    does not need to be updated when new analysis types are added.

    Attributes
    ----------
    name : str
        Human-readable result name (e.g. "Avoided emissions — CI portfolio").
    analysis_type : str
        Machine-readable analysis type key (e.g. ``"avoided_emissions"``).
        Downstream code uses this to decide how to interpret the results.
    summary : dict
        Global aggregate values (e.g. ``{"n_sites": 42, …}``).
    records : list of AnalysisRecord, optional
        Per-entity aggregated results.  Defaults to ``None``.
    time_series : list of AnalysisTimeStep, optional
        Per-entity-per-year observations.  Defaults to ``None``.
    data : dict, optional
        Free-form supplementary data (configuration echo, diagnostics, …).
        Defaults to ``None``.
    type : ResultType
        Discriminator — always ``ResultType.ANALYSIS_RESULTS``.
    """

    class Meta:
        unknown = marshmallow.EXCLUDE

    name: str
    analysis_type: str
    summary: dict
    records: typing.Optional[typing.List[AnalysisRecord]] = None
    time_series: typing.Optional[typing.List[AnalysisTimeStep]] = None
    data: typing.Optional[dict] = None
    type: ResultType = dataclasses.field(
        default=ResultType.ANALYSIS_RESULTS,
        metadata={
            "by_value": True,
            "validate": validate.Equal(ResultType.ANALYSIS_RESULTS),
        },
    )
