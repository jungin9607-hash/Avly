"""explain.py 와 adjustment_explanations.json 테스트. 표준 라이브러리만 쓴다.

실행 (backend/model 폴더에서):  python -m unittest avly.test_explain -v
"""
import re
import unittest

from . import explain
from .dataio import load_json
from .tables import ADJUSTMENT_RULES, FACTOR_LABELS, LAW_ARTICLES_BY_TYPE


PLACE_QUESTIONS = {'residential_area'}


class DataTests(unittest.TestCase):
    def setUp(self):
        self.data = load_json('adjustment_explanations.json')

    def test_every_factor_in_labels_and_rules_has_an_explanation(self):
        used = {rule['factor'] for config in ADJUSTMENT_RULES.values() for rule in config['rules']}
        self.assertEqual(set(self.data['factors']), set(FACTOR_LABELS))
        self.assertTrue(used <= set(self.data['factors']), used - set(self.data['factors']))

    def test_official_label_matches_current_label(self):
        for key, entry in self.data['factors'].items():
            self.assertEqual(entry['label'], FACTOR_LABELS[key], key)

    def test_sentences_follow_the_writing_rules(self):
        for key, entry in self.data['factors'].items():
            for field in ('title', 'easy', 'question'):
                self.assertTrue(entry[field].strip(), (key, field))
            if key not in PLACE_QUESTIONS:  # 장소에 대한 질문은 누구 얘기가 아니므로 {who} 가 없다
                self.assertIn('{who}', entry['question'], key)
            self.assertTrue(entry['question'].endswith('?'), key)
            self.assertNotIn('{', entry['title'] + entry['easy'], key)
            # 과실이 늘고 줄어드는 방향은 effect 템플릿이 붙이므로 설명에는 쓰지 않는다
            self.assertNotRegex(entry['easy'], r'과실이 (더해|늘|줄|커|무거워)', key)

    def test_every_law_article_used_by_the_rules_is_listed(self):
        used = {str(article) for articles in LAW_ARTICLES_BY_TYPE.values() for article in articles}
        self.assertTrue(used <= set(self.data['laws']), used - set(self.data['laws']))

    def test_laws_are_not_marked_reviewed_before_a_person_checks_them(self):
        self.assertFalse(self.data['_meta']['reviewed'])
        for key, entry in self.data['laws'].items():
            self.assertFalse(entry['reviewed'], key)

    def test_a_factor_marked_reviewed_has_complete_wording(self):
        # 가감요소 문장은 검수가 진행 중이다. 검수 완료 표시가 붙었다면 서비스가 그대로 쓰므로 제목·설명·질문이 빠짐없이 있어야 한다.
        for key, entry in self.data['factors'].items():
            if not entry['reviewed']:
                continue
            for field in ('title', 'easy', 'question'):
                self.assertTrue(entry[field].strip(), (key, field))
            self.assertIn('{who}', entry['question'], key)
            self.assertTrue(entry['question'].strip().endswith('?'), key)


class ExplainTests(unittest.TestCase):
    def test_base_sentence(self):
        self.assertEqual(explain.explain_base(30, 70)['text'], '이런 사고의 기본 책임은 내 차 30% : 상대 차 70%예요.')
        self.assertIsNone(explain.explain_base(30, 70)['situation'])
        s = explain.explain_base(40, 60, '직선 도로', '후행 직진', '선행 진로변경')['situation']
        self.assertEqual(s, "직선 도로에서 내 차는 '후행 직진', 상대 차는 '선행 진로변경' 상황이에요.")

    def test_factor_increase_and_decrease(self):
        up = explain.explain_factor('signal_delay', 10, '상대 차')
        self.assertEqual(up['effect'], '상대 차 과실 +10%p')
        self.assertTrue(up['question'].startswith('상대 차가'))
        self.assertFalse(up['missing'])
        down = explain.explain_factor('protruding_wait_exit', -10, '내 차')
        self.assertEqual(down['effect'], '내 차 과실 -10%p')

    def test_factor_effect_keeps_fractions_but_drops_trailing_zero(self):
        self.assertEqual(explain.explain_factor('slow_failure', 7.5, '내 차')['effect'], '내 차 과실 +7.5%p')
        self.assertEqual(explain.explain_factor('slow_failure', 10.0, '내 차')['effect'], '내 차 과실 +10%p')

    def test_unknown_factor_falls_back_to_marked_label(self):
        r = explain.explain_factor('not_registered', 10, '내 차')
        self.assertTrue(r['missing'])
        self.assertIsNone(r['easy'])
        self.assertEqual(r['title'], 'not_registered')

    def test_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            explain.explain_factor('signal_delay', 10, '나')
        with self.assertRaises(ValueError):
            explain.explain_factor('signal_delay', 0, '내 차')

    def test_law_known_unwritten_and_unknown(self):
        self.assertFalse(explain.explain_law(38)['missing'])
        self.assertIn('차의 신호', explain.explain_law('38')['name'])
        self.assertTrue(explain.explain_law('25의2')['missing'])
        self.assertTrue(explain.explain_law(999)['missing'])


if __name__ == '__main__':
    unittest.main()
