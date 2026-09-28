import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.jev_windows.app.cloud_ocr import CloudReader, parse_transcription
from integrations.jev_windows.core import experience
from integrations.jev_windows.core.deepseek_strategy import parse_choice, parse_evidence
from integrations.jev_windows.core.trend import load_csv


class WindowsSyncTest(unittest.TestCase):
    def test_cloud_ocr_requires_explicit_speaker_and_dedupes(self):
        lines = parse_transcription(json.dumps({"messages": [
            {"side": "them", "text": "明天见？"}, {"side": "me", "text": "好"}]}))
        reader = CloudReader("deepseek", "deepseek-flash", "dummy")
        self.assertEqual(reader.new_lines(lines), [("her", None, "明天见？"), ("me", None, "好")])
        self.assertEqual(reader.new_lines(lines), [])
        with self.assertRaisesRegex(ValueError, "说话人"):
            parse_transcription('{"messages":[{"side":"unknown","text":"你好"}]}')

    def test_deepseek_evidence_and_token_weights_are_distinct(self):
        evidence = parse_evidence('{"strategy":"降压","confidence":0.62,"intent":"可能在忙",'
                                  '"facts":["对方说今天忙"],"unknowns":["何时有空"]}')
        self.assertEqual(evidence["method"], "deepseek_self_report")
        self.assertEqual(evidence["weights"], {})
        labels = dict(zip("ABCDEFG", ("承接", "降压", "调侃", "轻推", "约见", "澄清", "收线")))
        top = [{"token": c, "logprob": -.1 if c == "B" else -3.0} for c in "ABCDEFG"]
        weights = parse_choice("B", {"content": [{"token": "B", "top_logprobs": top}]}, labels)
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertGreater(weights["降压"], weights["承接"])

    def test_details_and_rewrite_use_verified_own_words(self):
        messages = [("me", "行，周六见"), ("her", "好呀")]
        result = {"candidates": ["那周六见吧", "好的，周六见"], "goutou": {"action": "承接"}}
        responses = [json.dumps({"intent": "愿意继续聊", "facts": ["对方说好呀"],
                                 "hypotheses": [], "unknowns": ["具体时间"], "next_step": "确定时间"}),
                     '["行，周六见","好，周六见"]',
                     '{"scores":[{"id":0,"score":60},{"id":1,"score":40}]}']
        with patch.object(experience, "_ask", side_effect=responses) as ask:
            detail = experience.details(messages, "朋友", result, provider="deepseek", model="m", key="dummy")
            rewritten, weights = experience.rewrite(messages, result, provider="deepseek", model="m", key="dummy")
        self.assertIn("对方说好呀", detail)
        self.assertEqual(rewritten, ["行，周六见", "好，周六见"])
        self.assertEqual(weights, [.6, .4])
        self.assertEqual(ask.call_args_list[1].args[1]["my_samples"], ["行，周六见"])

    def test_candidate_reason_includes_tradeoff(self):
        result = {"candidates": ["好，周六见"], "goutou": {"action": "承接"}}
        with patch.object(experience, "_ask", return_value='{"reason":"接住邀约",'
                         '"tradeoff":"还需要确认时间"}'):
            text = experience.explain([("her", "周六见吗")], "朋友", result, 0,
                                      provider="deepseek", model="m", key="dummy")
        self.assertIn("接住邀约", text)
        self.assertIn("还需要确认时间", text)

    def test_csv_requires_dates_and_calculates_direction_balance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat.csv"
            path.write_text("timestamp,sender,message\n2026-09-01 10:00:00,other,你好\n"
                            "2026-09-01 10:01:00,me,好\n2026-09-02 12:00:00,other,周末见\n",
                            encoding="utf-8")
            rows = load_csv(path)
        self.assertEqual([(r.open, r.high, r.low, r.close) for r in rows],
                         [(0, 1, 0, 0), (0, 1, 0, 1)])


if __name__ == "__main__":
    unittest.main()
