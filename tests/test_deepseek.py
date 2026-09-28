"""Offline provider isolation and response tests; never access real Keychain."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations" / "jev_mac"))
from client import Config, DEEPSEEK_BASE, OPENROUTER_BASE, complete


class DeepSeekTests(unittest.TestCase):
    def test_saved_key_defaults_to_official_provider(self):
        with patch.dict(os.environ, {}, clear=True), patch("client.read_deepseek_keychain", return_value="saved"):
            config = Config.from_env()
        self.assertEqual((config.base, config.model, config.key), (DEEPSEEK_BASE, "deepseek-flash", "saved"))
        self.assertNotIn("saved", repr(config))

    def test_custom_or_partial_config_never_inherits_key(self):
        for env in ({"GOUTOU_MODEL": "other"}, {"GOUTOU_API_KEY": "explicit"},
                    {"GOUTOU_API_BASE": "https://example.com/v1", "GOUTOU_MODEL": "other"},
                    {"GOUTOU_API_BASE": DEEPSEEK_BASE + ".example.com", "GOUTOU_MODEL": "other"},
                    {"GOUTOU_API_BASE": DEEPSEEK_BASE + "/other", "GOUTOU_MODEL": "other"}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), \
                    patch("client.read_deepseek_keychain") as read:
                with self.assertRaises(ValueError):
                    Config.from_env()
                read.assert_not_called()

    def test_explicit_official_route_can_use_saved_key(self):
        for base in (DEEPSEEK_BASE, DEEPSEEK_BASE + "/v1"):
            with patch.dict(os.environ, {"GOUTOU_API_BASE": base}, clear=True), \
                    patch("client.read_deepseek_keychain", return_value="saved"):
                self.assertEqual(Config.from_env().key, "saved")

    def test_explicit_credentials_take_precedence(self):
        env = {"GOUTOU_API_BASE": DEEPSEEK_BASE, "GOUTOU_MODEL": "chosen", "GOUTOU_API_KEY": "explicit"}
        with patch.dict(os.environ, env, clear=True), patch("client.read_deepseek_keychain") as read:
            config = Config.from_env()
        read.assert_not_called()
        self.assertEqual((config.model, config.key), ("chosen", "explicit"))

    def test_openrouter_key_is_bound_to_its_official_route(self):
        with patch('client.read_openrouter_keychain', return_value='openrouter-test-key'), \
                patch('client.read_deepseek_keychain') as deepseek:
            config = Config.openrouter('openrouter/free')
        self.assertEqual((config.base, config.model, config.key),
                         (OPENROUTER_BASE, 'openrouter/free', 'openrouter-test-key'))
        self.assertEqual(config.endpoint, 'https://openrouter.ai/api/v1/chat/completions')
        self.assertNotIn('openrouter-test-key', repr(config))
        deepseek.assert_not_called()

    def test_openrouter_without_own_key_fails(self):
        with patch('client.read_openrouter_keychain', return_value=''), \
                patch('client.read_deepseek_keychain') as deepseek:
            with self.assertRaisesRegex(ValueError, 'OpenRouter Key'):
                Config.openrouter()
        deepseek.assert_not_called()

    def test_saved_openrouter_selection_routes_reply_without_deepseek_key(self):
        saved = {'reply_provider': 'openrouter', 'base': OPENROUTER_BASE,
                 'model': 'openrouter/free'}
        with patch.dict(os.environ, {}, clear=True), \
                patch('client.read_openrouter_keychain', return_value='or-key'), \
                patch('client.read_deepseek_keychain') as deepseek:
            config = Config.for_preferences(saved)
        self.assertEqual((config.base, config.model, config.key),
                         (OPENROUTER_BASE, 'openrouter/free', 'or-key'))
        deepseek.assert_not_called()

    def test_explicit_environment_overrides_saved_openrouter_selection(self):
        saved = {'reply_provider': 'openrouter', 'base': OPENROUTER_BASE,
                 'model': 'openrouter/free'}
        env = {'GOUTOU_API_BASE': DEEPSEEK_BASE, 'GOUTOU_MODEL': 'deepseek-flash',
               'GOUTOU_API_KEY': 'env-only'}
        with patch.dict(os.environ, env, clear=True), \
                patch('client.read_openrouter_keychain') as openrouter:
            config = Config.for_preferences(saved)
        self.assertEqual((config.base, config.model, config.key),
                         (DEEPSEEK_BASE, 'deepseek-flash', 'env-only'))
        openrouter.assert_not_called()

    def test_provider_options_and_truncation(self):
        for base in (DEEPSEEK_BASE, "https://example.com/v1"):
            response = Mock()
            response.read.return_value = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}).encode()
            opener = Mock()
            opener.open.return_value.__enter__ = Mock(return_value=response)
            opener.open.return_value.__exit__ = Mock(return_value=False)
            with patch("urllib.request.build_opener", return_value=opener):
                self.assertEqual(complete(Config(base, "m", "secret"), []), "{}")
                body = json.loads(opener.open.call_args[0][0].data)
                self.assertEqual("thinking" in body, base == DEEPSEEK_BASE)
                self.assertEqual("response_format" in body, base == DEEPSEEK_BASE)
                if base == DEEPSEEK_BASE:
                    self.assertEqual(body["thinking"], {"type": "disabled"})
                response.read.return_value = json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}).encode()
                with self.assertRaisesRegex(ValueError, "未完整"):
                    complete(Config(base, "m", "secret"), [])

    def test_openrouter_ocr_requests_json_without_deepseek_only_options(self):
        response = Mock()
        response.read.return_value = json.dumps({
            'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}).encode()
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch('urllib.request.build_opener', return_value=opener):
            complete(Config(OPENROUTER_BASE, 'openrouter/free', 'or-test-key'), [], json_mode=True)
        body = json.loads(opener.open.call_args.args[0].data)
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertNotIn('thinking', body)

    def test_deepseek_choice_requests_first_token_logprobs_without_json_mode(self):
        response = Mock()
        response.read.return_value = json.dumps({'choices': [{'finish_reason': 'stop',
            'message': {'content': 'B'}, 'logprobs': {'content': [
                {'token': 'B', 'top_logprobs': [{'token': 'B', 'logprob': -.1}]}]}}]}).encode()
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch('urllib.request.build_opener', return_value=opener):
            content, logprobs = complete(Config(DEEPSEEK_BASE, 'deepseek-flash', 'key'), [],
                                         choice_logprobs=True)
        body = json.loads(opener.open.call_args.args[0].data)
        self.assertEqual(content, 'B')
        self.assertEqual(logprobs['content'][0]['token'], 'B')
        self.assertEqual((body['logprobs'], body['top_logprobs']), (True, 20))
        self.assertNotIn('response_format', body)
