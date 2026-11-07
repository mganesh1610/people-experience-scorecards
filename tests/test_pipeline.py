import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pipeline import numeric, delta, comparison_status, normalize_score

class Boundaries(unittest.TestCase):
    def test_unavailable_is_not_zero(self):
        self.assertEqual(numeric(('[c]',None)),(None,'[c]'))
        self.assertEqual(numeric(('0','0')),(0.0,None))
    def test_out_of_range_is_rejected(self):
        for n in ['-0.1','100.1','nan','inf']:
            with self.assertRaises(ValueError): numeric((n,n))
    def test_scope_change_blocks_delta(self):
        a=dict(entity_name='A',department_group='B',organisation_note='')
        b=dict(entity_name='A',department_group='C',organisation_note='')
        self.assertEqual(comparison_status(a,b),'review_scope')
        self.assertIsNone(delta(30,40,'review_scope'))
    def test_missing_previous_not_imputed(self):
        self.assertIsNone(delta(None,40,'same_reported_scope'))
        self.assertEqual(comparison_status(None,{}),'new_or_unmatched')
    def test_percentage_points_not_relative_percent(self):
        self.assertEqual(delta(30,40,'same_reported_scope'),10)
    def test_zero_is_valid(self):
        self.assertEqual(delta(0,1,'same_reported_scope'),1)
    def test_published_response_anomaly_is_retained(self):
        self.assertEqual(normalize_score(('103.398','103.398'),'response_rate'),
                         (None,'source_out_of_range:103.398'))
    def test_notes_require_review(self):
        a=dict(entity_name='A',department_group='B',organisation_note='Includes agencies')
        self.assertEqual(comparison_status(a,a),'review_scope')

if __name__=='__main__': unittest.main()
