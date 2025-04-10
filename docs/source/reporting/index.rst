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

The primary changes to the schemas used for UNCCD reporting for the 2024
reporting cycle relative to the 2020 reporting cycle are to suport an arbitrary
number of reporting periods, with the potential for multiple reports (of
different types) for each period. This change was made to allow reporting both
on the "Period Assessment" as well as the "Status" for each reporting period
(using the terminology of the SDG 15.3.1. GPG Addendum).

The Period Assessment and Status reports are contained in
:class:`te_schemas.reporting.LandConditionReport` objects within a `dict` in the 
`land_condition` field of the
:class:`te_schemas.reporting.TrendsEarthLandConditionSummary` object. The keys within that
`dict` are used to distinguish the Status reports from the Period Assessments -
Status reports have the period name followed by "_status". The keys are
sequentially named, as "Report_1", "Report_2", etc., where "Report_1" is the
Period Assessment for the first reporting period, and "Report_1_status", the
Status report for the first reporting period.

TODOS:
- List renames of classes that were done for clarity
