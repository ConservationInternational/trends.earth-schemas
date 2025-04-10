Usage in reporting
========================

Overview of reporting format
____________________________

UNCCD Strategic Objectives 1 and 2
++++++++++++++++++++++++++++++++++

The report for UNCCD Strategic Objectives 1 and 2 is generated using the schema
:class:`te_schemas.reporting.TrendsEarthLandConditionSummary`. Three objects
are contained within that report:

- Report metadata using the :class:`te_schemas.reporting.ReportMetadata`
  schema, including the version of Trends.Earth used for the analysis, the
  title of the report, the data it was generated, and the polygon indicating
  the boundary for the area analyzed.
- A `dict` where the keys are period names and the items
  :class:`te_schemas.reporting.LandConditionReport` with reports on land
  condition for each period.
- A `dict` where the keys are period names and the items
  :class:`te_schemas.reporting.AffectedPopulationReport` with reports for the
  periods included in the analysis.


UNCCD Strategic Objective 3
++++++++++++++++++++++++++++++++++

The report for UNCCD Strategic Objective 3 is generated using the schema
:class:`te_schemas.reporting.TrendsEarthDroughtSummary`. Two objects
are contained within that report:

- Report metadata using the :class:`te_schemas.reporting.ReportMetadata`
  schema, including the version of Trends.Earth used for the analysis, the
  title of the report, the data it was generated, and the polygon indicating
  the boundary for the area analyzed.
- A :class:`te_schemas.reporting.DroughtReport` object containing summaries of
  the Tier 1, 2, and 3 drought indicators.


Format changes relative to 2020 reporting cycle
-----------------------------------------------

- Renames of classes:
  - TODO: Summarize
- Changes in schema:
  - TODO: Discuss additions to handle multiple reporting periods
  - TODO: Discuss additions to handle new status datasets
