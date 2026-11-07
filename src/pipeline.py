#!/usr/bin/env python3
"""Reproducible, aggregate-only employee experience scorecards."""
import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
P = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
O = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
SOURCES = {
    2024: 'https://assets.publishing.service.gov.uk/media/67974db0fadfcd21351e28dc/Civil_Service_People_Survey_2024_Benchmark_Results.ods',
    2023: 'https://assets.publishing.service.gov.uk/media/65d8b79e87005a001180f911/Civil_Service_People_Survey_2023_Benchmark_Results.ods',
}
METRICS = {
    'response_rate': ('Survey response rate', 'Participation', 'Higher'),
    'EES': ('Employee engagement index', 'Engagement', 'Higher'),
    'HSE_index': ('Proxy Stress Index', 'Wellbeing', 'Lower'),
    'PERMA_index': ('PERMA Index', 'Wellbeing', 'Higher'),
    'mw_ts': ('My work', 'Experience', 'Higher'),
    'op_ts': ('Organisational objectives and purpose', 'Experience', 'Higher'),
    'lm_ts': ('My manager', 'Experience', 'Higher'),
    'mt_ts': ('My team', 'Experience', 'Higher'),
    'ld_ts': ('Learning and development', 'People growth', 'Higher'),
    'if_ts': ('Inclusion and fair treatment', 'Inclusion', 'Higher'),
    'rw_ts': ('Resources and workload', 'Workforce planning', 'Higher'),
    'pb_ts': ('Pay and benefits', 'Total rewards', 'Higher'),
    'lc_ts': ('Leadership and managing change', 'Change', 'Higher'),
}


def cell_value(cell):
    text = '\n'.join(''.join(p.itertext()) for p in cell.findall(P+'p')).strip()
    return text, cell.get(O+'value')


def ods_rows(blob, table_name='Table_3'):
    """Expand bounded repeated cells, retaining source numerical values."""
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        root = ET.fromstring(archive.read('content.xml'))
    tables = [x for x in root.iter(T+'table') if x.get(T+'name') == table_name]
    if len(tables) != 1:
        raise ValueError('Expected exactly one named source table')
    output = []
    for row in tables[0].findall(T+'table-row'):
        cells = []
        for c in row:
            if c.tag not in (T+'table-cell', T+'covered-table-cell'):
                continue
            repeats = int(c.get(T+'number-columns-repeated', '1'))
            if repeats > 300:
                # ODS programs may encode the unused sheet tail as 16K blank cells.
                if cell_value(c) != ('', None):
                    raise ValueError('Unexpected nonblank repeated tail')
                break
            cells.extend([cell_value(c)]*repeats)
        repeats = int(row.get(T+'number-rows-repeated', '1'))
        if repeats > 300:
            if any(text or number is not None for text, number in cells):
                raise ValueError('Unexpected nonblank repeated rows')
            continue
        output.extend([cells]*repeats)
    return output


def numeric(value):
    text, raw_number = value
    if raw_number is None:
        return None, text or 'blank'
    number = float(raw_number)
    if not 0 <= number <= 100:
        raise ValueError('Score outside 0-100')
    return number, None


def normalize_score(value, metric):
    text, raw = value
    if metric == 'response_rate' and raw is not None and not 0 <= float(raw) <= 100:
        return None, 'source_out_of_range:'+raw
    return numeric(value)


def normalize(blob, year):
    rows = ods_rows(blob)
    header_index = next(i for i, row in enumerate(rows) if row and row[0][0] == 'Organisation')
    header = rows[header_index]
    mapping = {}
    for index, (text, _) in enumerate(header):
        key = 'response_rate' if text.startswith('Survey response rate') else text.split('\n')[0].rstrip('.')
        if key in METRICS:
            mapping[key] = index
    if set(mapping) != set(METRICS):
        raise ValueError('Missing or changed metric header: '+str(set(METRICS)-set(mapping)))
    records = []
    entities = []
    for row in rows[header_index+1:]:
        if len(row) < 5 or not re.fullmatch(r'[A-Z][A-Z0-9_]*', row[0][0]):
            continue
        entity, name, department, note = [c[0] for c in row[:4]]
        kind = 'benchmark' if entity in ('CS_MEAN', 'CS_MEDIAN') else 'reported_entity'
        entities.append(dict(survey_year=year, entity_code=entity, entity_name=name,
                             department_group=department, organisation_note=note, entity_kind=kind))
        for metric, index in mapping.items():
            score, missing = normalize_score(row[index] if index < len(row) else ('', None), metric)
            records.append(dict(survey_year=year, entity_code=entity, metric_code=metric,
                                score_pct=score, missing_reason=missing))
    if len(entities) != len({r['entity_code'] for r in entities}):
        raise ValueError('Duplicate entity code')
    return entities, records


def comparison_status(previous, current):
    if previous is None:
        return 'new_or_unmatched'
    if (previous['entity_name'] != current['entity_name'] or
        previous['department_group'] != current['department_group'] or
        previous['organisation_note'] or current['organisation_note']):
        return 'review_scope'
    return 'same_reported_scope'


def delta(previous, current, status):
    if status != 'same_reported_scope' or previous is None or current is None:
        return None
    return round(current-previous, 6)


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run(data_dir=None, output=None):
    data_dir = data_dir or ROOT/'data'
    output = output or ROOT/'results'
    data_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    lock_path = ROOT/'source_lock.json'
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    all_entities, all_scores, provenance = [], [], []
    for year, url in sorted(SOURCES.items()):
        path = data_dir/f'csps_{year}.ods'
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if str(year) in lock and lock[str(year)] != digest:
            raise ValueError('Source hash changed; inspect before updating source_lock.json')
        lock[str(year)] = digest
        entities, scores = normalize(blob, year)
        all_entities.extend(entities)
        all_scores.extend(scores)
        provenance.append(dict(year=year, url=url, bytes=len(blob), sha256=digest,
                               entities=len(entities), selected_score_cells=len(scores)))
    if not lock_path.exists():
        lock_path.write_text(json.dumps(lock, indent=2)+'\n')
    db = sqlite3.connect(output/'people_experience.sqlite')
    db.executescript('''
      PRAGMA foreign_keys=ON;
      DROP VIEW IF EXISTS scorecard;
      DROP TABLE IF EXISTS scores; DROP TABLE IF EXISTS entities; DROP TABLE IF EXISTS metrics;
      CREATE TABLE entities(survey_year INTEGER,entity_code TEXT,entity_name TEXT,
          department_group TEXT,organisation_note TEXT,entity_kind TEXT,
          PRIMARY KEY(survey_year,entity_code));
      CREATE TABLE metrics(metric_code TEXT PRIMARY KEY,label TEXT,capability TEXT,favourable_direction TEXT);
      CREATE TABLE scores(survey_year INTEGER,entity_code TEXT,metric_code TEXT,
          score_pct REAL CHECK(score_pct BETWEEN 0 AND 100),missing_reason TEXT,
          PRIMARY KEY(survey_year,entity_code,metric_code),
          FOREIGN KEY(survey_year,entity_code) REFERENCES entities(survey_year,entity_code),
          FOREIGN KEY(metric_code) REFERENCES metrics(metric_code));
      CREATE VIEW scorecard AS SELECT e.*,s.metric_code,m.label,m.capability,
          m.favourable_direction,s.score_pct,s.missing_reason
          FROM entities e JOIN scores s USING(survey_year,entity_code)
          JOIN metrics m USING(metric_code);
    ''')
    db.executemany('INSERT INTO entities VALUES(?,?,?,?,?,?)', (tuple(r.values()) for r in all_entities))
    db.executemany('INSERT INTO metrics VALUES(?,?,?,?)', ((code,*values) for code,values in METRICS.items()))
    db.executemany('INSERT INTO scores VALUES(?,?,?,?,?)', (tuple(r.values()) for r in all_scores))
    db.commit()
    db.row_factory = sqlite3.Row
    scorecard = [dict(r) for r in db.execute('SELECT * FROM scorecard ORDER BY survey_year,entity_code,metric_code')]
    previous = {r['entity_code']:r for r in all_entities if r['survey_year']==2023}
    score_index = {(r['survey_year'],r['entity_code'],r['metric_code']):r['score_pct'] for r in all_scores}
    comparisons = []
    for entity in [r for r in all_entities if r['survey_year']==2024 and r['entity_kind']=='reported_entity']:
        status = comparison_status(previous.get(entity['entity_code']), entity)
        for metric in METRICS:
            old = score_index.get((2023,entity['entity_code'],metric))
            new = score_index.get((2024,entity['entity_code'],metric))
            comparisons.append(dict(entity_code=entity['entity_code'],metric_code=metric,
                previous_year=2023,current_year=2024,previous_score_pct=old,
                current_score_pct=new,comparability=status,
                change_pp=delta(old,new,status)))
    write_csv(output/'scorecard.csv', scorecard)
    write_csv(output/'year_comparison.csv', comparisons)
    write_csv(output/'metric_dictionary.csv', [dict(metric_code=k,label=v[0],capability=v[1],
               favourable_direction=v[2],unit='percentage points on a 0-100 scale',
               aggregation='Non-additive. Select exactly one entity, year and measure.') for k,v in METRICS.items()])
    checks = {
        'score_row_conservation':len(scorecard)==len(all_scores),
        'unique_score_keys':len(all_scores)==len({(r['survey_year'],r['entity_code'],r['metric_code']) for r in all_scores}),
        'complete_metric_grid':len(all_scores)==len(all_entities)*len(METRICS),
        'score_bounds':all(r['score_pct'] is None or 0<=r['score_pct']<=100 for r in all_scores),
        'missing_not_zero':all((r['score_pct'] is None)==(r['missing_reason'] is not None) for r in all_scores),
        'foreign_keys':not list(db.execute('PRAGMA foreign_key_check')),
        'database_integrity':db.execute('PRAGMA integrity_check').fetchone()[0]=='ok',
        'two_distinct_benchmarks':all(score_index.get((y,'CS_MEDIAN','EES')) is not None and score_index.get((y,'CS_MEAN','EES')) is not None for y in SOURCES),
        'scope_changed_delta_withheld':all(r['change_pp'] is None for r in comparisons if r['comparability']!='same_reported_scope'),
        'no_person_identifiers':not any(x in scorecard[0] for x in ['employee_id','email','salary','name','caller_id']),
    }
    if not all(checks.values()):
        raise ValueError('Validation failed: '+str(checks))
    result = dict(sources=provenance,metric_definitions=len(METRICS),score_cells=len(all_scores),
        missing_score_cells=sum(r['score_pct'] is None for r in all_scores),
        out_of_range_source_cells=[r for r in all_scores if (r['missing_reason'] or '').startswith('source_out_of_range:')],
        current_reported_entities=sum(r['survey_year']==2024 and r['entity_kind']=='reported_entity' for r in all_entities),
        comparison_cells=len(comparisons),comparable_delta_cells=sum(r['change_pp'] is not None for r in comparisons),
        review_scope_cells=sum(r['comparability']=='review_scope' for r in comparisons),
        checks=checks,checks_passed=sum(checks.values()),
        execution='Python standard library and SQLite. Power BI DAX and Power Query are import handoffs.',
        interpretation='Organisation scores are not additive; respondent-level sample sizes are unavailable. No significance or causal improvement is inferred.')
    (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'schema.json').write_text(json.dumps({t:[dict(r) for r in db.execute(f'PRAGMA table_info({t})')] for t in ['entities','metrics','scores']},indent=2)+'\n')
    db.close()
    build_dashboard(output, scorecard, result)
    return result


def build_dashboard(output, rows, result):
    data = json.dumps(rows).replace('</','<\\/')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>People Experience Scorecards</title>
<style>body{font:16px Arial;color:#20272c;background:#f5f7fa;margin:30px auto;max-width:1000px;padding:20px}h1{color:#173b55}select{font:inherit;padding:8px;margin-right:12px}table{width:100%;border-collapse:collapse;background:white;margin-top:20px}th,td{text-align:left;padding:12px;border-bottom:1px solid #dce1e6}.muted{color:#526274}th{background:#173b55;color:white}.bar{display:inline-block;height:10px;background:#376f94;margin-right:8px}.status{padding:12px;background:#e9eef3}</style>
<h1>People Experience Scorecards</h1><p>Employee engagement, development, inclusion, rewards and workload measures.</p>
<label>Survey year <select id="year"><option>2024</option><option>2023</option></select></label><label>Reported entity <select id="entity"></select></label>
<p class="status" id="scope"></p><table><thead><tr><th>Measure</th><th>Score (%)</th><th>Favourable direction</th></tr></thead><tbody id="body"></tbody></table>
<p class="muted">Source: UK Cabinet Office, Civil Service People Survey 2023 and 2024. Scores are non-additive. Civil Service mean and median benchmarks remain distinct. Selection does not establish statistical significance or a causal explanation.</p>
<script>const rows=__DATA__;const y=document.querySelector('#year'),e=document.querySelector('#entity');
function options(){const entities=[...new Map(rows.filter(r=>r.survey_year==y.value).map(r=>[r.entity_code,r.entity_name])).entries()];e.replaceChildren(...entities.map(([k,v])=>new Option(v,k)));e.value='CS_MEAN';paint()}
function paint(){const chosen=rows.filter(r=>r.survey_year==y.value&&r.entity_code==e.value);document.querySelector('#body').innerHTML=chosen.map(r=>`<tr><td>${r.label}</td><td>${r.score_pct===null?'Unavailable':`<span class="bar" style="width:${r.score_pct}px"></span>${r.score_pct.toFixed(1)}`}</td><td>${r.favourable_direction}</td></tr>`).join('');document.querySelector('#scope').textContent=chosen.length?chosen[0].entity_name+' | '+chosen[0].department_group+' | '+(chosen[0].organisation_note||'No organisation note supplied'):''}y.onchange=options;e.onchange=paint;options();</script></html>'''.replace('__DATA__',data)
    (output/'dashboard.html').write_text(html)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    print(json.dumps(run(args.data_dir,args.output),indent=2))
