"""Persist display/model preferences only; no keys, chat or relationship text."""
import json
import os
from pathlib import Path

PATH = Path(__file__).with_name("settings.local.json")
OCR_METHODS = ('vision', 'deepseek', 'openrouter')
REPLY_PROVIDERS = ('deepseek', 'openrouter')
STRATEGY_PROVIDERS = ('auto', 'jev', 'deepseek')


def load(path=PATH):
    try:
        data = json.loads(path.read_text())
        if (not isinstance(data, dict) or not isinstance(data.get("model"), str)
                or not isinstance(data.get("base"), str) or len(data["model"]) > 160
                or isinstance(data.get("opacity"), bool)
                or not isinstance(data.get("opacity"), (float, int))
                or not 55 <= data["opacity"] <= 100):
            return {}
        from experience import ReplyPreferences
        options = data.get('reply', {})
        reply = ReplyPreferences(**options)
        result = {key: data[key] for key in ("model", "base", "opacity")}
        ocr_method = data.get('ocr_method', 'vision')
        if ocr_method not in OCR_METHODS:
            return {}
        result['ocr_method'] = ocr_method
        ocr_model = data.get('ocr_model', 'openrouter/free')
        if not isinstance(ocr_model, str) or not 1 <= len(ocr_model.strip()) <= 160:
            return {}
        result['ocr_model'] = ocr_model.strip()
        provider = data.get('reply_provider', 'deepseek')
        if provider not in REPLY_PROVIDERS:
            return {}
        result['reply_provider'] = provider
        strategy_provider = data.get('strategy_provider', 'auto')
        if strategy_provider not in STRATEGY_PROVIDERS:
            return {}
        result['strategy_provider'] = strategy_provider
        if options:
            result['reply'] = {'tone': reply.tone, 'length': reply.length, 'count': reply.count}
        return result
    except (OSError, ValueError, TypeError):
        return {}


def save(model, base, opacity, path=PATH, reply=None, ocr_method='vision',
         reply_provider='deepseek', ocr_model='openrouter/free', strategy_provider='auto'):
    if ocr_method not in OCR_METHODS:
        raise ValueError('请选择有效的 OCR 识别方式')
    if reply_provider not in REPLY_PROVIDERS:
        raise ValueError('请选择有效的回复接口')
    if strategy_provider not in STRATEGY_PROVIDERS:
        raise ValueError('请选择有效的策略判断接口')
    if not isinstance(ocr_model, str) or not 1 <= len(ocr_model.strip()) <= 160:
        raise ValueError('请填写有效的 OpenRouter 识图模型 ID')
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            data = {"model": model, "base": base, "opacity": opacity,
                    "ocr_method": ocr_method, "reply_provider": reply_provider,
                    "ocr_model": ocr_model.strip(), "strategy_provider": strategy_provider}
            if reply:
                data['reply'] = {'tone': reply.tone, 'length': reply.length, 'count': reply.count}
            json.dump(data, stream)
        os.replace(temporary, path)
    except OSError:
        raise ValueError("无法保存设置，请检查目录写入权限") from None
