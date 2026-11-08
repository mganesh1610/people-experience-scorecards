# Schema and methods

## Source mapping

The parser reads `Table_3` from each ODS. Source `Organisation`, `Organisation name`, `Department group` and `Organisation notes` map to `entity_code`, `entity_name`, `department_group` and `organisation_note`. `survey_year` comes from the explicitly selected source file, not a timestamp guess. Header code suffixes differ between 2023 and 2024; terminal dots are normalised without changing metric identities.

| Source header code | Metric | Rule |
| --- | --- | --- |
| Survey response rate (%) | response_rate | Published participation rate; out-of-range values withheld and retained in missing_reason |
| EES | Employee engagement index | Published weighted composite; not a simple mean of organisation scores |
| HSE_index | Proxy Stress Index | Lower is favourable |
| PERMA_index | PERMA Index | Higher is favourable |
| mw_ts, op_ts, lm_ts, mt_ts | Work, objectives, manager, team | Published percent-positive themes |
| ld_ts, if_ts, rw_ts | Development, inclusion, resources/workload | Published percent-positive themes |
| pb_ts, lc_ts | Pay/benefits, leadership/change | Published percent-positive themes |

Every entity has exactly 13 selected records. `score_pct` uses a 0-100 scale, not a fractional 0-1 scale. A missing or withheld value is SQLite NULL / CSV blank, with a reason. A real zero remains zero. `CS_MEAN` and `CS_MEDIAN` remain separate benchmark records. `reported_entity` includes organisation and group rows, including overlapping parent scopes.

`results/schema.json` contains exact SQLite types, nullability and keys. SQLite enforces unique composite keys, foreign keys and score bounds. The pipeline independently reconciles the source cell grid, joined output row count and key cardinality.

## Comparison formulation

For exactly one entity and metric: `change_pp = score_2024 - score_2023`, only if both scores exist and reported names/groups match with no organisation note requiring scope review. A changed name/group or any note produces `review_scope`; unmatched entities produce `new_or_unmatched`. No aggregate of organisation scores is substituted for a published national benchmark.

Stress changes should be read with lower-is-favourable direction. All other selected measures use higher-is-favourable direction.

## Validation

Ten data checks: source/join row conservation, unique keys, complete 13-metric grid, score bounds, missing-value preservation, referential integrity, SQLite integrity, distinct mean/median benchmarks, withheld scope-change deltas and absence of person identifiers in the public export. Eight tests exercise zero versus missing, bounds/NaN/infinity, source anomaly preservation, changed groups, organisation notes, unmatched years and percentage-point calculation.
