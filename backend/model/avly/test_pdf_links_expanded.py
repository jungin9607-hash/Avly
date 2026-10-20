"""133개 문서 연결과 수치·조건 차이 검증. API/DB를 사용하지 않습니다."""
import copy
import unittest
from collections import Counter

from . import pdf_reference as pdf


class ExpandedLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=pdf.read_rows(pdf.find_csv())
        cls.raw,cls.charts=pdf.load_reference(pdf.DEFAULT_REFERENCE)
        cls.links=pdf.load_json(pdf.DEFAULT_LINKS)
        cls.source_hash=cls.raw['original_collection_metadata']['source_sha256']
        cls.results={int(r['accident_type']):pdf.compare_row(r,cls.charts,cls.links,cls.source_hash) for r in cls.rows}
    def test_every_csv_row_has_one_document_link(self):
        self.assertEqual(set(self.results),set(range(133)))
        self.assertEqual(len(self.links['entries']),133)
        self.assertTrue(all(e['source_document_link'] for e in self.results.values()))
        self.assertTrue(all(e['source_document_link']['official_chart_id'] in self.charts for e in self.results.values()))
    def test_status_counts_are_explicit(self):
        self.assertEqual(Counter(e['status'] for e in self.results.values()),{
            'document_link_checked':103,'condition_derived_reference':19,
            'source_condition_review':5,'base_mismatch':5,'source_conflict':1})
    def test_direct_matches_have_same_base_and_role(self):
        for e in self.results.values():
            if e['status']=='document_link_checked':
                self.assertTrue(e['base_pair_matches'])
                self.assertTrue(e['role_mapping_verified'])
            self.assertFalse(e['rule_engine_ready'])
    def test_embedded_factors_proven_and_not_applied_twice(self):
        for e in self.results.values():
            if e['status']!='condition_derived_reference':continue
            self.assertTrue(e['effective_base_matches'])
            self.assertTrue(e['embedded_adjustments'])
            chart=self.charts[e['source_document_link']['official_chart_id']]
            mapped=pdf._mapped_rows(chart,e['source_document_link'],'A')
            for proof in e['embedded_adjustments']:
                match=next(r for r in mapped if r['raw_text']==proof['raw_text'])
                self.assertTrue(match['already_in_csv_base'])
                self.assertFalse(match['may_apply_again'])
    def test_nonprotected_turn_conflict_is_not_normalized(self):
        e=self.results[79]
        self.assertEqual(e['csv_base_pair'],[80,20])
        self.assertEqual(e['pdf_base_pairs_in_csv_order'],[[90,10]])
        self.assertEqual(e['status'],'base_mismatch')
    def test_reverse_parking_conflict_preserves_both_sources(self):
        e=self.results[127]
        self.assertEqual(e['status'],'source_conflict')
        self.assertEqual(e['csv_base_pair'],[25,75])
        self.assertEqual(e['pdf_base_pairs_in_csv_order'],[[30,70]])
        self.assertIn('+10',e['source_document_link']['notice'])
        self.assertIn('+5',e['source_document_link']['notice'])
    def test_signal_branches_and_geometry_kept_separate(self):
        self.assertEqual(self.results[69]['source_document_link']['official_chart_id'],'차3-5')
        self.assertEqual(self.results[76]['source_document_link']['official_chart_id'],'차2-5')
        self.assertEqual(self.results[22]['source_document_link']['variant_label'],'(다)')
        self.assertEqual(self.results[23]['source_document_link']['variant_label'],'(나)')
    def test_swapped_csv_roles_for_right_turn_and_roundabout(self):
        for key in (89,106,111,115,116,118,128,129):
            self.assertEqual(self.results[key]['source_document_link']['csv_A_pdf_role'],'B',key)
    def test_changed_csv_cannot_reuse_checked_mapping(self):
        row=copy.deepcopy(self.rows[60]);row['vehicle_a_progress_info_name']='[적색신호] 직진'
        e=pdf.compare_row(row,self.charts,self.links,self.source_hash)
        self.assertEqual(e['status'],'csv_changed')
    def test_changed_embedded_proof_is_not_accepted(self):
        charts=copy.deepcopy(self.charts)
        charts['차13-1']['adjustment_table']['adjustment_row_candidates']=[]
        e=pdf.compare_row(self.rows[28],charts,self.links,self.source_hash)
        self.assertEqual(e['status'],'source_proof_invalid')
    def test_web_all_types_have_bounded_reference_payload(self):
        import json
        for key in self.results:
            r=pdf.web_pdf_reference(key,'A')
            self.assertEqual(len(r['documents']),1,key)
            self.assertEqual(r['csv_accident_type'],key)
            self.assertNotIn('base64',json.dumps(r))
            self.assertFalse(r['calculation_modified'])
    def test_conflict_does_not_assign_service_actors(self):
        r=pdf.web_pdf_reference(127,'A')
        self.assertTrue(all(x['service_actor'] is None for x in r['documents'][0]['adjustment_candidates']))
    def test_missing_type_returns_explicit_unavailable(self):
        self.assertEqual(pdf.web_pdf_reference(999,'A')['status'],'reference_unavailable')
        self.assertEqual(pdf.web_pdf_reference(None,None)['status'],'no_scenarios')


if __name__=='__main__':unittest.main(verbosity=2)
