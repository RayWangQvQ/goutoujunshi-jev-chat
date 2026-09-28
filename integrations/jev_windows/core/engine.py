# -*- coding: utf-8 -*-
"""整条链的唯一入口：对话 → Jev 判断 → 带着判断起草 3 条 → Jev 排序 → 结构化结果。

平台无关。SSE 消费者、悬浮窗、命令行 demo 都只调 analyze()。
"""
from __future__ import annotations

try:
    from .draft import draft_candidates
    from .jev_client import JevError, ask
    from .goutou import brief, explicit_boundary
    from .questions import JUDGE_QUESTIONS, build_rank_question, build_state, guidance_text
    from .deepseek_strategy import decide as deepseek_decide, rank as deepseek_rank
except ImportError:
    from draft import draft_candidates
    from jev_client import JevError, ask
    from goutou import brief, explicit_boundary
    from questions import JUDGE_QUESTIONS, build_rank_question, build_state, guidance_text
    from deepseek_strategy import decide as deepseek_decide, rank as deepseek_rank

_REPLY_IDX = {"reply_a": 0, "reply_b": 1, "reply_c": 2}


def _add_usage(total: dict, one: dict | None) -> None:
    """两次 Jev 调用的 usage 相加（tokens、cost）；非数字的字段后来的盖掉前面的。"""
    for k, v in (one or {}).items():
        total[k] = total.get(k, 0) + v if isinstance(v, (int, float)) else v


def analyze(messages: list, relationship: str, model: str | None = None,
            timeout: float = 30, context: int = 10, provider: str = "deepseek",
            base_url: str | None = None, reply_to: str | None = None, style: str = "",
            thinking: bool = False, jev_provider: str = "openrouter",
            jev_model: str | None = None, strategy_provider: str = "jev",
            strategy_model: str = "deepseek-flash", strategy_key: str = "") -> dict:
    """messages: [(from, text)] from ∈ {her, me}，最新一条在最后；
    群聊里可以带第三项 name（说这句话的人），单聊不带。
    context: 起草和判断各看最近多少条消息（用户设置里的「参考上下文」）。
    provider: 起草走哪家（core.providers.DRAFT_PROVIDERS），base_url 只有自定义来源要传。
    jev_provider / jev_model: 判断和排序走哪家、哪个模型（core.providers.JEV_PROVIDERS）。
    reply_to: 群聊里指定回复给谁；None = 正常回复。
    style: 用户自己描述的说话风格，只影响起草。
    thinking: 起草时是否开思考模式，只影响起草，默认关。
    model / jev_model = None 用该来源的默认模型。

    返回 {candidates, best_index, best_reply, scores, answers, usage, reply_to}。
    scores 是每条候选的胜出概率（0~1），取自 best_reply.probabilities，取不到记 0.0。
    只有对方最新说话时才有意义调它——是不是该触发由调用方判断（看 latest_from）。

    三段式：先让 Jev 答 7 道判断题，把判断当小抄喂给起草，最后 Jev 只排序。
    首次判断失败时停止，不在缺少策略依据的情况下盲起草。usage 是两次之和。
    """
    state = build_state(messages, relationship, keep=context, reply_to=reply_to)
    if explicit_boundary(messages):
        reading = brief(messages, {})
        return {"candidates": [], "best_index": None, "best_reply": None,
                "scores": [], "answers": {}, "usage": {}, "reply_to": reply_to,
                "goutou": reading}
    if strategy_provider == "deepseek":
        decision = deepseek_decide(messages[-context:], relationship, strategy_model,
                                   strategy_key, timeout=timeout)
        guidance = (f"独立策略判断：{decision['strategy']}。可能的意图：{decision['intent']}。"
                    "已知事实：" + "；".join(decision["facts"]) + "。关键未知：" +
                    "；".join(decision["unknowns"]))
        candidates = draft_candidates(messages, relationship, provider=provider, model=model,
                                      base_url=base_url, timeout=timeout, keep=context,
                                      reply_to=reply_to, style=style, thinking=thinking,
                                      guidance=guidance)
        scores = deepseek_rank(messages[-context:], relationship, decision["strategy"],
                               candidates, strategy_model, strategy_key, timeout=timeout)
        best_index = max(range(len(scores)), key=lambda i: scores[i]) if scores else (
            0 if candidates else None)
        reading = {
            "facts": decision["facts"], "intent": decision["intent"],
            "intent_confidence": decision["confidence"] if decision["facts"] else None,
            "action": f"本轮主策略：{decision['strategy']}",
            "unknown": "；".join(decision["unknowns"]) or "完整上下文和对方内心仍未知",
            "next_step": "先核对原文，再按主策略选择候选；必要时先不回复。",
            "stop_condition": "对方明确拒绝或要求停止联系时停止推进。",
            "evidence_note": ("DeepSeek 三次标签轮换的首 token 权重只用于策略相对选择；"
                              "判断把握不是对方真实意图概率，候选权重不是回复成功率。")}
        return {"candidates": candidates, "best_index": best_index,
                "best_reply": candidates[best_index] if best_index is not None else None,
                "scores": scores, "answers": {}, "usage": {}, "reply_to": reply_to,
                "goutou": reading, "strategy_decision": decision}
    usage: dict = {}
    answers: dict = {}
    judged = False
    first = ask(state, dict(JUDGE_QUESTIONS), timeout=timeout,
                provider=jev_provider, model=jev_model)
    answers = first.get("answers") or {}
    if not isinstance(answers, dict) or any(
            not isinstance(answers.get(name), dict) for name in JUDGE_QUESTIONS):
        raise JevError("Jev 判断结果不完整，已停止生成回复；请重试")
    _add_usage(usage, first.get("usage"))
    judged = True

    candidates = draft_candidates(messages, relationship, provider=provider, model=model,
                                  base_url=base_url, timeout=timeout, keep=context,
                                  reply_to=reply_to, style=style, thinking=thinking,
                                  guidance=guidance_text(answers) if judged else None)
    if not candidates:
        return {"candidates": [], "best_index": None, "best_reply": None,
                "scores": [], "answers": answers, "usage": usage,
                "reply_to": reply_to, "goutou": brief(messages, answers)}

    questions = {} if judged else dict(JUDGE_QUESTIONS)
    if len(candidates) >= 2:  # 起草只给了 1 条就没什么可排的，判断题照问
        questions.update(build_rank_question(candidates))
    if questions:
        try:
            second = ask(state, questions, timeout=timeout,
                         provider=jev_provider, model=jev_model)
        except JevError:
            if not judged:  # 老路只有这一次调用，挂了就是挂了
                raise
            second = {}  # 判断还在，只是没排上序：下面按第一条推荐
        answers = {**answers, **(second.get("answers") or {})}
        _add_usage(usage, second.get("usage"))

    best_key = (answers.get("best_reply") or {}).get("choice")
    best_index = _REPLY_IDX.get(best_key, 0)  # 解析不出就退第一条
    if best_index >= len(candidates):
        best_index = 0

    probabilities = (answers.get("best_reply") or {}).get("probabilities") or {}
    scores = [0.0, 0.0, 0.0]
    for key, idx in _REPLY_IDX.items():
        try:
            scores[idx] = float(probabilities.get(key, 0.0))
        except (TypeError, ValueError):
            scores[idx] = 0.0  # 脏数据一律按 0 处理

    return {
        "candidates": candidates,
        "best_index": best_index,
        "best_reply": candidates[best_index],
        "scores": scores,
        "answers": answers,
        "usage": usage,
        "reply_to": reply_to,
        "goutou": brief(messages, answers),
    }
