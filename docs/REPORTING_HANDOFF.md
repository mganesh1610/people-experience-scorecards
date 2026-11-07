# Reporting requirements and ownership

| Business question | Measure / acceptance criterion | Accountable partner |
| --- | --- | --- |
| How are employees experiencing work? | Select one entity/year; show engagement and nine theme measures with their definitions | Employee experience owner |
| Where should a discussion begin? | Show observed workload, inclusion, development and rewards scores; keep interpretation and proposed actions in separate narrative fields | Relevant capability owner |
| Is a change comparable? | Withhold a delta when names, department groups or organisation notes require review | Analyst and source data owner |
| Is the score valid? | Missing stays blank, zero stays zero, anomalies have a source locator and reason | People information / source owner |
| Can managers self-serve safely? | Approve aggregate-only export, access groups, export policy and refresh ownership before publication | BI administrator and data owner |

## Repeatable reporting procedure

1. Run the hash-checked ingestion and validation. Investigate a changed hash before accepting a new publication.
2. Reconcile record counts and benchmark definitions, then inspect source exceptions and changed-scope rows.
3. Import `scorecard.csv` and `year_comparison.csv`. Relate by entity/metric only within a selected year-comparison context. Never relate only by entity and accidentally multiply rows.
4. In Power BI, use the supplied DAX's single-entity/year/metric selection guard. Configure refresh credentials, workspace roles, approved audiences and export restrictions in the tenant. The public dashboard contains only previously published aggregates and has no authentication layer.
5. Write a short narrative with separate Observed result, Interpretation, Recommended next step and Known limitation fields. A low score alone does not establish cause or justify an individual personnel decision.
6. Assign source defects to the system owner and measure-definition questions to the relevant capability owner. The analyst documents and escalates; the pipeline never writes back to a source system.

## Experience-backing boundary

This implementation provides an inspectable reference for metric definitions, data preparation, exception reconciliation, survey interpretation and reporting procedures. Historical employment claims must be supported by employer/portfolio evidence. Running this project does not prove that a historical employer used it or realised a particular percentage improvement.
