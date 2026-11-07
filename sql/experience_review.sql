-- One selection per entity/year; national mean and median are distinct rows.
WITH selected AS (
  SELECT entity_code, entity_name, metric_code, label, score_pct, missing_reason
  FROM scorecard
  WHERE survey_year = 2024 AND entity_code = 'CS_MEAN'
)
SELECT * FROM selected ORDER BY metric_code;

-- Exceptions sent to the source owner, not silently zero-filled.
SELECT survey_year, entity_code, metric_code, missing_reason
FROM scores WHERE score_pct IS NULL;

-- Counterpart and source-scope review remains separate from a numeric delta.
SELECT survey_year, COUNT(*) AS entity_rows
FROM entities GROUP BY survey_year;
