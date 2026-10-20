"""PDF web integration tests; no database, network or paid model calls."""
import unittest

from app import catalog
from app.worker.finalize import build_result
from app.worker.snapshot import from_model_result


def snapshot():
    return {'situation':{'summary':'테스트','road_shape':'직선 도로','candidates':[]},'timeline':[],'impact':{}}


class PDFWebTests(unittest.TestCase):
    def test_all_types_and_roles_keep_the_csv_base(self):
        for type_id,row in catalog.rows().items():
            for role in ('A','B'):
                result=build_result(snapshot(),{'accident_type_id':type_id,'role':role,'answers':{}},[])
                expected={'me':row.negligence_a,'other':row.negligence_b} if role=='A' else {'me':row.negligence_b,'other':row.negligence_a}
                self.assertEqual(result['fault']['base'],expected,(type_id,role))
                ref=result['pdf_reference']
                self.assertEqual(len(ref['documents']),1,(type_id,role))
                self.assertEqual(ref['documents'][0]['service_base_pair'],list(expected.values()))
                self.assertFalse(ref['calculation_modified'])
    def test_existing_solid_line_calculation_stays_10_90(self):
        answers={q['key']:'아니요' for q in catalog.adjustment_questions(11,'A')}
        answers['other.prohibited_change']='예'
        result=build_result(snapshot(),{'accident_type_id':11,'role':'A','answers':answers},[])
        self.assertEqual(result['fault']['final'],{'me':10,'other':90})
        self.assertEqual(result['pdf_reference']['documents'][0]['official_chart_id'],'차43-2')
    def test_pdf_rules_are_now_used_for_new_types(self):
        result=build_result(snapshot(),{'accident_type_id':60,'role':'A','answers':{}},[])
        self.assertEqual(result['state'],'partial')
        self.assertTrue(result['adjustments']['registered'])
        self.assertEqual(result['pdf_reference']['documents'][0]['official_chart_id'],'차1-1')
    def test_unresolved_type_does_not_get_arbitrary_reference(self):
        result=build_result(snapshot(),{'accident_type_id':None,'role':None,'answers':{}},[])
        self.assertEqual(result['state'],'unresolved')
        self.assertEqual(result['pdf_reference']['documents'],[])
    def test_snapshot_keeps_reference_status_without_full_document(self):
        data={'scene':{'contact':'미확인'},'pdf_reference_context':{
            'status':'linked','edition':'2023-06','entries':[{'csv_accident_type':11,'status':'document_link_checked','source_document_link':{'official_chart_id':'차43-2'}}],
            'documents':[{'text':'not copied into compact snapshot'}]}}
        result=from_model_result(data,'avly')
        self.assertEqual(result['pdf_reference']['entries'][0]['csv_accident_type'],11)
        self.assertNotIn('documents',result['pdf_reference'])


if __name__=='__main__':unittest.main(verbosity=2)
