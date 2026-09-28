import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations' / 'jev_mac'))
from client import Config, DEEPSEEK_BASE
from core import Snapshot
from deepseek_strategy import LABELS, config, decide, parse_choice, parse_decision
from pipeline import analyze_snapshot


class DeepSeekStrategyTests(unittest.TestCase):
    def test_uses_only_dedicated_deepseek_key(self):
        with patch('deepseek_strategy.read_deepseek_keychain', return_value=''):
            with self.assertRaisesRegex(ValueError, 'DeepSeek Key'):
                config()
        with patch('deepseek_strategy.read_deepseek_keychain', return_value='test-key'):
            self.assertEqual(config().key, 'test-key')

    def test_rejects_invalid_strategy_or_unbounded_confidence(self):
        with self.assertRaisesRegex(ValueError, '格式不正确'):
            parse_decision(json.dumps({'strategy': '操控', 'confidence': .5}), 'deepseek-flash')
        for confidence in (2, True, '不确定'):
            result = parse_decision(json.dumps({'strategy': '降压', 'confidence': confidence}),
                                    'deepseek-flash')
            self.assertIsNone(result.confidence)

    def test_nonessential_evidence_shape_does_not_block_valid_strategy(self):
        raw = json.dumps({'strategy':'降压', 'confidence':'0.62',
                          'facts':[{'text':'对方说忙'}, '下周未定'] * 4,
                          'unknowns':'此前是否有过约定', 'boundary':'不确定'}, ensure_ascii=False)
        result = parse_decision(raw, 'deepseek-flash')
        self.assertEqual(result.confidence, .62)
        self.assertEqual(result.evidence['unknowns'], ['此前是否有过约定'])
        self.assertEqual(len(result.evidence['facts']), 5)

    def test_invalid_first_response_gets_short_repair_request(self):
        snapshot = Snapshot('对象 A', '对方：这周忙')
        repaired = json.dumps({'strategy':'降压', 'confidence':None,
                               'facts':['对方说忙']}, ensure_ascii=False)
        with patch('deepseek_strategy.complete', side_effect=[
                '{bad-json', repaired, ('A', None)]) as call:
            result = decide(Config(DEEPSEEK_BASE, 'deepseek-flash', 'key'), snapshot, '邀约推进', '')
        self.assertEqual(call.call_count, 3)
        self.assertEqual(result.strategy, '降压')
        self.assertIsNone(result.confidence)
        self.assertEqual(result.method, 'deepseek_self_report')

    def test_uncertain_speaker_does_not_show_token_weight(self):
        snapshot = Snapshot('对象 A', '说话人待确认：你好 [OCR待核对]')
        evidence = json.dumps({'strategy':'澄清', 'confidence':.8}, ensure_ascii=False)
        with patch('deepseek_strategy.complete', return_value=evidence) as call:
            result = decide(Config(DEEPSEEK_BASE, 'deepseek-flash', 'key'), snapshot, '日常回复', '')
        self.assertEqual(call.call_count, 1)
        self.assertIsNone(result.confidence)
        self.assertEqual(result.probabilities, {})

    def test_deepseek_decision_uses_context_and_strategy_guide(self):
        snapshot = Snapshot('对象 A', '对方：这周忙，下周再说')
        evidence = json.dumps({'facts':['对方说这周忙'], 'unknowns':['下周是否有空'],
                               'boundary':'none', 'strategy':'降压', 'confidence':.62}, ensure_ascii=False)
        def response(cfg, messages, **kwargs):
            if kwargs.get('json_mode'):
                return evidence
            selected = next(label for label in LABELS if f'{label}=降压' in messages[0]['content'])
            top = [{'token':label, 'logprob':-.2 if label == selected else -3.0}
                   for label in LABELS]
            return selected, {'content':[{'token':selected, 'top_logprobs':top}]}
        with patch('deepseek_strategy.complete', side_effect=response) as call:
            result = decide(Config(DEEPSEEK_BASE, 'deepseek-flash', 'test-key'),
                            snapshot, '邀约推进', '')
        self.assertEqual(result.strategy, '降压')
        self.assertEqual(result.method, 'deepseek_logprobs')
        self.assertAlmostEqual(sum(result.probabilities.values()), 1)
        self.assertEqual(call.call_count, 4)
        self.assertIn('strategy_guide', json.loads(call.call_args_list[0].args[1][1]['content']))
        self.assertIn('这周忙', call.call_args_list[0].args[1][1]['content'])
        self.assertTrue(all(item.kwargs.get('choice_logprobs') for item in call.call_args_list[1:]))

    def test_missing_or_unstable_token_weights_keep_labeled_deepseek_fallback(self):
        snapshot = Snapshot('对象 A', '对方：这周忙')
        evidence = json.dumps({'facts':['对方说忙'], 'strategy':'降压', 'confidence':.62}, ensure_ascii=False)
        with patch('deepseek_strategy.complete', side_effect=[
                evidence, ('A', {'content':[{'token':'A', 'top_logprobs':[
                    {'token':'A', 'logprob':-.2}]}]})]):
            result = decide(Config(DEEPSEEK_BASE, 'deepseek-flash', 'key'), snapshot, '邀约推进', '')
        self.assertEqual(result.method, 'deepseek_self_report')
        self.assertEqual(result.probabilities, {})
        self.assertEqual(result.confidence, .62)

    def test_conflicting_rotations_do_not_publish_strategy_weights(self):
        snapshot = Snapshot('对象 A', '对方：这周忙')
        evidence = json.dumps({'facts':['对方说忙'], 'strategy':'降压', 'confidence':.62}, ensure_ascii=False)
        calls = 0
        def response(cfg, messages, **kwargs):
            nonlocal calls
            if kwargs.get('json_mode'):
                return evidence
            calls += 1
            preferred = '降压' if calls < 3 else '轻推'
            selected = next(label for label in LABELS if f'{label}={preferred}' in messages[0]['content'])
            top = [{'token':label, 'logprob':-.1 if label == selected else -4.0}
                   for label in LABELS]
            return selected, {'content':[{'token':selected, 'top_logprobs':top}]}
        with patch('deepseek_strategy.complete', side_effect=response):
            result = decide(Config(DEEPSEEK_BASE, 'deepseek-flash', 'key'), snapshot, '邀约推进', '')
        self.assertEqual(calls, 3)
        self.assertEqual(result.method, 'deepseek_self_report')
        self.assertEqual(result.probabilities, {})

    def test_choice_parser_requires_first_token_and_all_seven_labels(self):
        labels = dict(zip(LABELS, ('承接', '降压', '调侃', '轻推', '约见', '澄清', '收线')))
        top = [{'token':label, 'logprob':-i} for i, label in enumerate(LABELS)]
        with self.assertRaisesRegex(ValueError, '权重不可用'):
            parse_choice('A', {'content':[{'token':' ', 'top_logprobs':top}]}, labels)
        with self.assertRaisesRegex(ValueError, '权重不可用'):
            parse_choice('A', {'content':[{'token':'A', 'top_logprobs':top[:-1]}]}, labels)
        result = parse_choice('A', {'content':[{'token':'A', 'top_logprobs':top}]}, labels)
        self.assertAlmostEqual(sum(result.values()), 1)

    def test_pipeline_pins_reply_to_independent_deepseek_strategy(self):
        snapshot = Snapshot('对象 A', '对方：这周忙')
        reply_config = Config('https://openrouter.ai/api/v1', 'openrouter/free', 'reply-key')
        strategy_config = Config(DEEPSEEK_BASE, 'deepseek-flash', 'strategy-key')
        advice = {'support':'收到','facts':['对方说忙'],'hypotheses':[], 'unknowns':[],
                  'intent':'可能暂时没空','intent_confidence':.6, 'strategy':'降压',
                  'recommendation':'先接住','next_step':'之后再看','stop_condition':'拒绝时停止',
                  'candidates':[], 'question':''}
        with patch('pipeline.decide_deepseek', return_value=parse_decision('{"strategy":"降压","confidence":0.62}', 'deepseek-flash')), \
             patch('pipeline.complete', return_value=json.dumps(advice, ensure_ascii=False)) as reply:
            result = analyze_snapshot(snapshot, '邀约推进', '', reply_config,
                                      deepseek_strategy_config=strategy_config)
        self.assertEqual(result['strategy_decision']['model'], 'deepseek-flash')
        self.assertEqual(result['strategy'], '降压')
        self.assertEqual(reply.call_args.args[0], reply_config)


if __name__ == '__main__':
    unittest.main()
