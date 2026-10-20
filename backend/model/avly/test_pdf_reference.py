"""오프라인 PDF 연결 검증: python -m unittest avly.test_pdf_reference -v"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from . import pdf_reference as pdf
from . import adjustments
from .context import ctx
from .tables import ADJUSTMENT_RULES


def payload(role='A'):
    return {'scenarios':[{'scenario_id':'11:'+role+':0','accident_type':11,
            'base_fault':{'A':30,'B':70} if role=='A' else {'A':70,'B':30},
            'dashcam_table_role':role,'eligible_for_adjustment':True,
            'table_progress':{'A':'후행 직진','B':'선행 진로변경'},
            'service_progress':{'A':'후행 직진','B':'선행 진로변경'}}],
            'factors':[{'actor':'B' if role=='A' else 'A','factor':'prohibited_change',
                        'value':'있음','status':'user'}]}


def strip_pdf(value):
    if isinstance(value,dict):
        return {k:strip_pdf(v) for k,v in value.items() if k not in
                ('pdf_reference_context','pdf_reference','pdf_source_evidence')}
    return [strip_pdf(x) for x in value] if isinstance(value,list) else value


class PDFReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=pdf.read_rows(pdf.find_csv())
        cls.raw,cls.charts=pdf.load_reference(pdf.DEFAULT_REFERENCE)
        cls.links=pdf.load_json(pdf.DEFAULT_LINKS)
        cls.source_hash=cls.raw['original_collection_metadata']['source_sha256']
    def setUp(self):
        self.old_csv=ctx.csv_path;self.old_table=ctx.table
        ctx.csv_path=pdf.find_csv()
        ctx.table=[dict(r,accident_type=int(r['accident_type'])) for r in self.rows]
    def tearDown(self):
        ctx.csv_path=self.old_csv;ctx.table=self.old_table
    def bundle(self,role='A'):
        p=payload(role)
        return {'rule_engine_input':p,'rule_engine_output':adjustments.evaluate_rule_input(p)}
    def test_complete_catalog_preserved(self):
        checked=[]
        for row in self.rows:
            e=pdf.compare_row(row,self.charts,self.links,self.source_hash)
            self.assertEqual(e['csv_row'],row)
            if e['status']=='document_link_checked':checked.append(int(row['accident_type']))
        self.assertTrue({1,3,11,21,27,126,128} <= set(checked))
        self.assertEqual(len(checked),103)
        self.assertEqual(len(self.charts),105)
    def test_real_calculation_not_changed(self):
        for role,expected in [('A',{'A':10,'B':90}),('B',{'A':90,'B':10})]:
            b=self.bundle(role);original=copy.deepcopy(b)
            pdf.attach_pdf_reference(b,ctx.csv_path)
            self.assertEqual(strip_pdf(b),original)
            self.assertEqual(b['rule_engine_output']['results'][0]['adjusted_fault'],expected)
            self.assertFalse(b['pdf_reference_context']['calculation_modified'])
    def test_service_actor_mapping_is_correct_for_both_roles(self):
        for role,actor in [('A','B'),('B','A')]:
            b=pdf.attach_pdf_reference(self.bundle(role),ctx.csv_path)
            r=b['rule_engine_output']['results'][0]
            self.assertTrue(any(x['pdf_table_actor']=='B' and x['service_actor']==actor
                                for x in r['pdf_reference']['adjustment_candidates']))
            f=r['applied_adjustments'][0]
            self.assertEqual(f['pdf_source_evidence']['status'],'text_role_value_match')
    def test_roundabout_csv_pdf_roles_reversed(self):
        ref=pdf.get_csv_reference(128)
        link=ref['comparison']['source_document_link']
        self.assertEqual(link['csv_A_pdf_role'],'B')
        self.assertEqual(link['csv_B_pdf_role'],'A')
        rows=pdf._mapped_rows(ref['documents'][0],link,'A')
        self.assertTrue(rows)
        for r in rows:
            if r['pdf_table_actor']=='A':self.assertEqual(r['service_actor'],'B')
    def test_unknown_roles_are_not_filled(self):
        ref=pdf.get_csv_reference(11)
        rows=pdf._mapped_rows(ref['documents'][0],ref['comparison']['source_document_link'],None)
        self.assertTrue(all(r['service_actor'] is None for r in rows))
    def test_unreviewed_type_has_no_automatic_document(self):
        ref=pdf.get_csv_reference(127)
        self.assertEqual(len(ref['documents']),1)
        self.assertEqual(ref['comparison']['status'],'source_conflict')
        self.assertFalse(ref['comparison']['role_mapping_verified'])
        self.assertEqual(ref['comparison']['review_candidates'],[])
        self.assertFalse(ref['rule_engine_ready'])
    def test_changed_csv_blocks_link(self):
        row=copy.deepcopy(self.rows[11]);row['negligence_a']='40';row['negligence_b']='60'
        result=pdf.compare_row(row,self.charts,self.links,self.source_hash)
        self.assertEqual(result['status'],'csv_changed')
        self.assertFalse(result['role_mapping_verified'])
    def test_changed_pdf_blocks_link(self):
        e=pdf.compare_row(self.rows[11],self.charts,self.links,'other edition')
        self.assertEqual(e['status'],'source_changed')
    def test_bad_base_is_rejected(self):
        p=payload();p['scenarios'][0]['base_fault']={'A':30,'B':90}
        with self.assertRaises(ValueError):adjustments.evaluate_rule_input(p)
    def test_missing_reference_does_not_break_existing_calculation(self):
        b=self.bundle();original=copy.deepcopy(b)
        with tempfile.TemporaryDirectory() as tmp:
            pdf.attach_pdf_reference(b,ctx.csv_path,reference_path=Path(tmp)/'missing.json')
        self.assertEqual(strip_pdf(b),original)
        self.assertEqual(b['pdf_reference_context']['status'],'unmapped_or_unavailable')
    def test_reference_kept_out_of_model_image_payload(self):
        b=pdf.attach_pdf_reference(self.bundle(),ctx.csv_path)
        text=json.dumps(b,ensure_ascii=False)
        self.assertNotIn('base64',text)
        self.assertNotIn('assets',self.raw)
        self.assertLess(len(text),300000)
    def test_same_type_deduplicates_documents(self):
        b=self.bundle();r=copy.deepcopy(b['rule_engine_output']['results'][0]);r['scenario_id']='other'
        b['rule_engine_output']['results'].append(r)
        pdf.attach_pdf_reference(b,ctx.csv_path)
        self.assertEqual(len(b['pdf_reference_context']['documents']),1)
        self.assertEqual(len(b['pdf_reference_context']['entries']),1)
    def test_empty_results_do_not_invent_reference(self):
        b=pdf.attach_pdf_reference({'rule_engine_output':{'results':[]}},ctx.csv_path)
        self.assertEqual(b['pdf_reference_context']['status'],'no_scenarios')
        self.assertEqual(b['pdf_reference_context']['documents'],[])
    def test_law_bundle_hook_attaches_pdf_without_api(self):
        b=self.bundle()
        with patch.object(adjustments,'law_rule_bundle_before_case_guard',return_value=b), \
             patch.object(adjustments,'sanitize_case_bundle',side_effect=lambda x:x):
            result=adjustments.law_rule_bundle(None,[])
        self.assertEqual(result['pdf_reference_context']['status'],'linked')
    def test_user_report_mentions_pdf_source(self):
        from .report import build_user_report
        b=pdf.attach_pdf_reference(self.bundle(),ctx.csv_path)
        scene=SimpleNamespace(_evidence_audit={})
        text=build_user_report(scene,{},[],[],bundle_override=b)
        self.assertIn('PDF 참고 기준: 차43-2',text)
        self.assertIn('2023.06',text)
    def test_existing_rules_are_not_mutated(self):
        before=copy.deepcopy(ADJUSTMENT_RULES)
        pdf.attach_pdf_reference(self.bundle(),ctx.csv_path)
        self.assertEqual(before,ADJUSTMENT_RULES)
    def test_links_are_available_via_package(self):
        self.assertEqual(pdf.DEFAULT_REFERENCE.parent,pdf.PACKAGE_DIR/'data/pdf_reference_2023')
        self.assertTrue(pdf.DEFAULT_REFERENCE.is_file())


if __name__=='__main__':unittest.main(verbosity=2)
