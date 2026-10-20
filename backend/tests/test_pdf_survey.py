"""PDF 설문·답변·계산 연결. DB/네트워크 없이 실행합니다."""
import copy
import unittest
from unittest.mock import patch

from app import catalog
from app.worker.finalize import build_result
from avly.pdf_rules import get_rule_config, registry
from avly import adjustments


def snapshot():return {'situation':{'summary':'테스트','candidates':[]},'timeline':[],'impact':{}}
def result(key,role='A',answers=None):
    return build_result(snapshot(),{'accident_type_id':key,'role':role,'answers':answers or {}},[])


class PDFSurveyTests(unittest.TestCase):
    def test_questions_generated_from_exact_source_rows(self):
        count=0
        for key in registry()['types']:
            config=get_rule_config(int(key))
            for role in ('A','B'):
                qs=catalog.adjustment_questions(int(key),role)
                self.assertEqual(len(qs),len(config['rules']))
                self.assertLessEqual(len(qs),60)
                self.assertEqual(len({q['key'] for q in qs}),len(qs))
                for q,r in zip(qs,config['rules']):
                    self.assertEqual(q['pdf_source']['raw_text'],r['pdf_source']['raw_text'])
                    self.assertTrue(q['question'])
                    self.assertEqual(q['delta_pp'],r['delta_pp'])
                    self.assertEqual(q['who'],'내 차' if r['actor']==role else '상대 차')
                    count+=1
        self.assertGreater(count,1500)
    def test_parking_question_titles_use_pdf_terms_not_old_examples(self):
        qs=catalog.adjustment_questions(126,'A')
        by_key={q['key']:q for q in qs}
        self.assertEqual(by_key['me.slow_failure']['question'],'내 차 · 서행불이행')
        self.assertEqual(by_key['me.gross_negligence']['question'],'내 차 · 현저한 과실')
        self.assertEqual(by_key['me.serious_negligence']['pdf_factor'],'중대한 과실')
        self.assertEqual(by_key['other.slow_failure']['pdf_factor'],'서행불이행(급하게 출차)')
        self.assertEqual(by_key['other.protruding_wait_exit']['pdf_factor'],'차량 앞부분 내밀고 대기 후 출차')
        reversed_qs={q['key']:q for q in catalog.adjustment_questions(126,'B')}
        self.assertEqual(reversed_qs['me.slow_failure']['question'],'내 차 · 서행불이행(급하게 출차)')

    def test_all_no_answers_keep_base_for_every_supported_type_and_role(self):
        for key in registry()['types']:
            row=catalog.get_row(int(key))
            for role in ('A','B'):
                qs=catalog.adjustment_questions(int(key),role)
                value=result(int(key),role,{q['key']:'아니요' for q in qs})
                expected={'me':row.negligence_a,'other':row.negligence_b} if role=='A' else {'me':row.negligence_b,'other':row.negligence_a}
                self.assertEqual(value['fault']['adjusted'],expected,(key,role))
                self.assertTrue(value['adjustments']['registered'])
    def test_new_pdf_only_factor_affects_real_result(self):
        qs=catalog.adjustment_questions(4,'A')
        item=next(q for q in qs if '급박한 문 열림' in q['pdf_source']['raw_text'])
        answers={q['key']:'아니요' for q in qs};answers[item['key']]='예'
        r=result(4,answers=answers)
        self.assertEqual(r['fault']['base'],{'me':20,'other':80})
        self.assertEqual(r['fault']['adjusted'],{'me':10,'other':90})
        self.assertTrue(r['adjustments']['applied'][0]['title'])
    def test_unknown_answers_are_pending_not_zero(self):
        r=result(60)
        self.assertEqual(r['state'],'partial')
        self.assertTrue(r['adjustments']['pending'])
        self.assertIsNone(r['fault']['final'])
    def test_existing_solid_line_case_remains_10_90(self):
        qs=catalog.adjustment_questions(11,'A');answers={q['key']:'아니요' for q in qs}
        answers['other.prohibited_change']='예'
        self.assertEqual(result(11,answers=answers)['fault']['adjusted'],{'me':10,'other':90})
    def test_severity_group_does_not_add_10_and_20(self):
        qs=catalog.adjustment_questions(60,'A');answers={q['key']:'아니요' for q in qs}
        answers.update({'me.gross_negligence':'예','me.serious_negligence':'예'})
        self.assertEqual(result(60,answers=answers)['fault']['adjusted'],{'me':20,'other':80})
    def test_already_embedded_t_shape_and_prior_entry_not_asked_again(self):
        for key in (28,29,106,107,108,110,111):
            config=get_rule_config(key)
            for rule in config['rules']:
                self.assertNotIn(rule['pdf_source']['raw_text'],[p['raw_text'] for p in
                    __import__('avly.pdf_reference',fromlist=['get_csv_reference']).get_csv_reference(key)['comparison'].get('embedded_adjustments',[])])
    def test_branch_specific_factor_not_leaked(self):
        qs=catalog.adjustment_questions(62,'A')
        self.assertFalse(any('(가)' in q['pdf_source']['raw_text'] for q in qs))
    def test_conflicting_source_types_still_do_not_get_arbitrary_rules(self):
        for key in (2,55,56,57,79,86,87,88,120,123,127):
            self.assertEqual(catalog.adjustment_questions(key,'A'),[])
            self.assertEqual(result(key)['state'],'base_only')
    def test_parking_forward_type_does_not_ask_reverse(self):
        qs=catalog.adjustment_questions(126,'A')
        self.assertTrue(qs)
        self.assertTrue(all(not q['pdf_source']['raw_text'].endswith('후진 +10') for q in qs))
    def test_changed_csv_does_not_keep_pdf_rules(self):
        from avly import pdf_rules
        fake={'comparison':{'status':'csv_changed','csv_row':{}},'documents':[]}
        with patch.object(pdf_rules,'get_csv_reference',return_value=fake):
            self.assertIsNone(pdf_rules.get_rule_config(60))
    def test_registered_rules_are_not_mutated_by_user_answers(self):
        before=copy.deepcopy(registry())
        result(11,answers={'other.prohibited_change':'예'})
        self.assertEqual(registry(),before)
    def test_original_ai_suggestions_survive_for_known_factors(self):
        qs=catalog.adjustment_questions(11,'A',[{'actor':'B','factor':'prohibited_change','value':'있음','status':'observed','reason':'실선 관찰'}])
        q=next(q for q in qs if q['key']=='other.prohibited_change')
        self.assertEqual(q['suggested']['answer'],'예')
        self.assertEqual(q['suggested']['evidence'],'실선 관찰')


if __name__=='__main__':unittest.main(verbosity=2)
