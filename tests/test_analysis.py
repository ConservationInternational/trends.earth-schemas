"""Tests for te_schemas.analysis — generic analysis result schemas."""

from te_schemas.analysis import AnalysisRecord, AnalysisResults, AnalysisTimeStep
from te_schemas.results import ResultType


# ---------------------------------------------------------------------------
# AnalysisTimeStep
# ---------------------------------------------------------------------------


class TestAnalysisTimeStep:
    def test_round_trip(self):
        ts = AnalysisTimeStep(
            entity_id="SITE_001",
            year=2015,
            values={"forest_loss_avoided_ha": 1.5, "emissions_avoided_mgco2e": 50.2},
            entity_name="Alto Mayo",
            metadata={"n_matched_pixels": 120},
        )
        schema = AnalysisTimeStep.schema()
        dumped = schema.dump(ts)
        assert dumped["entity_id"] == "SITE_001"
        assert dumped["year"] == 2015
        assert dumped["values"]["emissions_avoided_mgco2e"] == 50.2
        assert dumped["entity_name"] == "Alto Mayo"

        loaded = schema.load(dumped)
        assert loaded.entity_id == ts.entity_id
        assert loaded.year == ts.year
        assert loaded.values == ts.values
        assert loaded.metadata == ts.metadata

    def test_minimal(self):
        ts = AnalysisTimeStep(
            entity_id="X",
            year=2020,
            values={"metric_a": 1.0},
        )
        schema = AnalysisTimeStep.schema()
        dumped = schema.dump(ts)
        loaded = schema.load(dumped)
        assert loaded.entity_name is None
        assert loaded.metadata is None


# ---------------------------------------------------------------------------
# AnalysisRecord
# ---------------------------------------------------------------------------


class TestAnalysisRecord:
    def test_round_trip(self):
        rec = AnalysisRecord(
            entity_id="SITE_001",
            values={
                "forest_loss_avoided_ha": 12.3,
                "emissions_avoided_mgco2e": 456.7,
                "area_ha": 500.0,
            },
            entity_name="Alto Mayo",
            period_start=2001,
            period_end=2020,
            metadata={"sampled_fraction": 0.85},
        )
        schema = AnalysisRecord.schema()
        dumped = schema.dump(rec)
        loaded = schema.load(dumped)
        assert loaded.entity_id == "SITE_001"
        assert loaded.period_start == 2001
        assert loaded.period_end == 2020
        assert loaded.values["area_ha"] == 500.0

    def test_minimal(self):
        rec = AnalysisRecord(entity_id="R1", values={"v": 0})
        schema = AnalysisRecord.schema()
        loaded = schema.load(schema.dump(rec))
        assert loaded.period_start is None
        assert loaded.period_end is None


# ---------------------------------------------------------------------------
# AnalysisResults
# ---------------------------------------------------------------------------


class TestAnalysisResults:
    def _make_sample(self):
        return AnalysisResults(
            name="Avoided emissions — CI portfolio",
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
                    },
                ),
            ],
            time_series=[
                AnalysisTimeStep(
                    entity_id="SITE_001",
                    year=2015,
                    values={"emissions_avoided_mgco2e": 50.2},
                ),
                AnalysisTimeStep(
                    entity_id="SITE_001",
                    year=2016,
                    values={"emissions_avoided_mgco2e": 55.0},
                ),
            ],
            data={"config_echo": {"min_site_area_ha": 100}},
        )

    def test_round_trip(self):
        ar = self._make_sample()
        schema = AnalysisResults.schema()
        dumped = schema.dump(ar)

        assert dumped["type"] == "AnalysisResults"
        assert dumped["analysis_type"] == "avoided_emissions"
        assert dumped["summary"]["n_sites"] == 42
        assert len(dumped["records"]) == 1
        assert len(dumped["time_series"]) == 2

        loaded = schema.load(dumped)
        assert loaded.name == ar.name
        assert loaded.analysis_type == ar.analysis_type
        assert loaded.summary == ar.summary
        assert len(loaded.records) == 1
        assert loaded.records[0].entity_id == "SITE_001"
        assert len(loaded.time_series) == 2
        assert loaded.time_series[0].year == 2015

    def test_type_discriminator(self):
        ar = self._make_sample()
        assert ar.type == ResultType.ANALYSIS_RESULTS

        dumped = AnalysisResults.schema().dump(ar)
        assert dumped["type"] == "AnalysisResults"

    def test_unknown_fields_excluded(self):
        """Extra fields in the input dict should be silently ignored."""
        ar = self._make_sample()
        dumped = AnalysisResults.schema().dump(ar)
        dumped["extra_unknown_field"] = "should be ignored"
        loaded = AnalysisResults.schema().load(dumped)
        assert not hasattr(loaded, "extra_unknown_field")

    def test_empty_records_and_time_series(self):
        ar = AnalysisResults(
            name="Empty test",
            analysis_type="test",
            summary={"n": 0},
        )
        schema = AnalysisResults.schema()
        loaded = schema.load(schema.dump(ar))
        assert loaded.records is None
        assert loaded.time_series is None
        assert loaded.data is None

    def test_results_field_dispatch(self):
        """AnalysisResults should be deserialised by ResultsField in jobs.py."""
        from te_schemas.jobs import ResultsField

        ar = self._make_sample()
        dumped = AnalysisResults.schema().dump(ar)

        field = ResultsField()
        loaded = field._deserialize(dumped, "results", {})
        assert isinstance(loaded, AnalysisResults)
        assert loaded.analysis_type == "avoided_emissions"

    def test_results_field_in_list(self):
        """AnalysisResults should work inside a list of results."""
        from te_schemas.jobs import ResultsField

        ar = self._make_sample()
        dumped = AnalysisResults.schema().dump(ar)

        field = ResultsField()
        loaded = field._deserialize([dumped], "results", {})
        assert isinstance(loaded, list)
        assert len(loaded) == 1
        assert isinstance(loaded[0], AnalysisResults)
