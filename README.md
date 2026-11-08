# People Experience Scorecards

A reproducible People Analytics project covering employee experience, inclusion, development, rewards, workload, benchmark definitions and confidential reporting boundaries. It uses published, organisation-level UK Cabinet Office Civil Service People Survey results.

## Run

Python 3.10 or newer. No third-party dependencies, account or paid service.

```sh
python3 src/pipeline.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory results
```

Open `http://localhost:8000/dashboard.html`. The two source ODS files are downloaded on the first run and checked against committed SHA-256 hashes on subsequent runs. Raw downloads and SQLite databases remain local. Compact aggregate CSVs, the dashboard and executed validation results are committed.

## Architecture

Cabinet Office ODS files -> bounded XML parser -> typed entity/metric contracts -> SQLite dimensional model -> reconciled scorecard and comparison CSVs -> interactive dashboard and Power BI / Qlik handoff scripts.

The model has three tables: `entities` keyed by survey year and entity code, `metrics` keyed by metric code, and `scores` keyed by year, entity and metric. The scorecard view joins them without multiplying source rows. SQL joins and CTE examples, Power Query M, DAX definitions, a Qlik load script, schema metadata and boundary tests accompany the pipeline.

## Executed results

- 2,782 selected score cells across 2023 and 2024, 13 metric definitions and 107 reported entities per year, including the separate Civil Service mean and median benchmarks.
- 1,365 current-entity/metric comparisons. 1,221 have a publishable numerical change under the implemented scope rule; 130 require scope review and 14 are unmatched or unavailable.
- One source response-rate anomaly (GPA, 2023, 103.398%) remains explicit as `source_out_of_range:103.398`, with its analytical score withheld. It is never capped, imputed as zero or silently dropped.
- All 10 pipeline validation checks and eight boundary tests passed.

Results are in `results/validation.json`. Python and SQLite execute the data model, with DAX, Power Query and Qlik files included for BI platform integration.

## Sources and interpretation

Primary: [Civil Service People Survey 2024](https://www.gov.uk/government/publications/civil-service-people-survey-2024-results), Cabinet Office, published 30 January 2025 and updated 6 May 2025. Backup/comparison: [2023 results](https://www.gov.uk/government/publications/civil-service-people-survey-2023-results). Files are published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Full direct file URLs and hashes are recorded in `results/validation.json` and `source_lock.json`.

Organisation/group rows can overlap and must not be summed into a workforce total. Response rates, theme scores, wellbeing indices and the engagement index are distinct constructs. Numerical deltas measure percentage-point changes under a consistent reported label/group.

See [schema and methods](docs/SCHEMA_AND_METHODS.md) and the [reporting handoff](docs/REPORTING_HANDOFF.md).
