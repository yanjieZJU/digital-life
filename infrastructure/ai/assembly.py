"""LLM 输入组装契约。

唯一组装函数 `assemble_llm_input(wake_id, call_seq, instance_id)` 是"一次 LLM 调用
实际收到什么 messages"的真理来源。它被两条路径调用：

- 发消息路径（`infrastructure/ai/agent.py` 的 `_chat()`）：在写库副作用完成后，
  调用本函数得到 final payload，发送。
- 回溯路径（`infrastructure/persistence/instance/runtime_log.py` 的
  `render_input_for_call`）：薄包装，直接调本函数，返回结果给前端字面渲染。

设计契约见 `docs/architecture/llm-input-assembly.md`。核心原则：

1. 数据库是唯一事实来源。本函数只从库读，不接运行期内存态。
2. 边界判据是 `llm_call_seq`，不是 timestamp。
3. dedup 在写库阶段完成；组装不做二次 dedup。
4. think 注入放在 turns+injections 的交错拼装之后；provider 守卫保证只 patch
   真实 assistant、跳过 fake-assistant（content=None 或带 tool_calls）。
5. 压缩（narrative 叙事替换）当前**不**在本函数内——由发消息路径在调用本函数之后
   再 yield to `_maybe_compress_messages`；回溯路径不压缩（见文档"按 narrative 存在性
   判断"段）。后续可把压缩也归并进来，本函数签名不变。

伪消息 id 规则（确定性约束）：
- 注入：`fake_{sys_tool}_{injection.id}`（已在 `runtime_log._injection_as_fake_pair` 实现）
- 叙事（未引入时预留）：`narrative_{segment_index:03d}`
"""
from __future__ import annotations

from typing import Any, Callable

from infrastructure.ai.providers import resolve_provider


def _injection_as_fake_pair(inj: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """注入行 → (fake assistant tool_call 占位, tool result)。

    与 ``runtime_log.RuntimeLogDB._injection_as_fake_pair`` 完全一致，行 id 做种子
    确保发消息和回溯产出同一个 tool_call_id。之所以在此重写一份（而非调静态方法），
    是为了让组装函数对结构变化自包含、可独立单测。

    **fake-assistant 标记**：与 tool_msg 一样给 assistant_msg 加 ``_is_fake=True``，
    让 provider 的 think 注入守卫能从"真实历史 assistant"中区分出注入占位
    （真实历史 assistant 即便 content=None、带 tool_calls，也应被 patch think；
     注入占位则应跳过）。
    """
    vir_id = f"fake_{inj['sys_tool']}_{inj['id']}"
    assistant_msg = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": vir_id,
            "type": "function",
            "function": {"name": inj["sys_tool"], "arguments": "{}"},
        }],
        "_is_fake": True,
    }
    tool_msg = {
        "role": "tool",
        "tool_call_id": vir_id,
        "name": inj["sys_tool"],
        "content": inj["content"] or "",
        "_is_fake": True,
        "_scope_id": inj.get("scope_id") or "*",
    }
    return assistant_msg, tool_msg


def _turn_to_message(t: dict[str, Any]) -> dict[str, Any]:
    """turn 行 → 发给 LLM 的 message dict。

    不带 reasoning 字段进 messages（组装阶段 reasoning 单独走 provider 注入路径）。
    """
    msg: dict[str, Any] = {"role": t["role"]}
    if t.get("content") is not None:
        msg["content"] = t["content"]
    if t.get("tool_name"):
        msg["name"] = t["tool_name"]
    if t.get("tool_calls"):
        msg["tool_calls"] = t["tool_calls"]
    if t.get("tool_call_id"):
        msg["tool_call_id"] = t["tool_call_id"]
    return msg


def assemble_llm_input(
    *,
    wake_id: int,
    call_seq: int,
    audit: Any,
    model: str | None = None,
    persona_loader: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """组装第 call_seq 次 LLM 调用实际收到的 messages（字面）。

    参数：
        wake_id: 该次 wake 的 id（turn/injection 表的外键）
        call_seq: 组装第几次调用（0-based）
        audit: ``RuntimeLogDB`` 实例——直接传 DB 句柄而非 instance_id，让该函数
               是真正的纯读函数（不依赖全局单例解析），可被单测用临时 DB 验证。
        model: 模型名（推断 provider 家族，决定 think 注入格式）。None 默认 GLM。
        persona_loader: 回退加 persona——当 wake.meta.system_prompt_text 缺失时，
                        用 meta.system_prompt_ref（形如 ``instance:<id>``）调 loader。

    返回：messages list，按"模型实际顺序"排好（system 在前、turns+injections 交错、
    最后 think 已拼回历史 assistant content）。

    边界：turns 严格取 `llm_call_seq < call_seq`，但显式追加 call 0 的 user action prompt。
    """
    if audit is None:
        return []

    wake = audit.get_wake(wake_id)
    if not wake:
        return []

    meta = wake.get("meta_json") or {}

    # ─ 四类输入（原始数据源） ─────────────────────────────────────────────
    # 注意：不能用 list_turns(up_to_call_seq=call_seq)——该 helper 的语义是
    # `llm_call_seq < up_to_call_seq`，对 call_seq==0 会返回空，连 call 0 的
    # user action prompt 都拿不到。我们改取全部 turns，再在分组阶段按 call_seq
    # 边界精确筛选：
    #   - 完整前序各 call 的全部 turns：seq < call_seq
    #   - 显式追加 call 0 的 user action prompt（仅当本 wake 是新启而非纯续接时存在）
    all_turns_raw: list[dict[str, Any]] = audit.list_turns(wake_id)
    all_turns: list[dict[str, Any]] = [
        t for t in all_turns_raw if int(t["llm_call_seq"]) < call_seq
    ]

    all_injs: list[dict[str, Any]] = audit.list_injections(wake_id)
    # dedup 在写库时已完成（inject() 对 latest 策略内置 DELETE-then-INSERT；
    # entity_recall 由 recall() 显式 DELETE 旧行）。按行序 id 重放即可。

    # ─ 思考注入子函数（provider 自带守卫：跳过 fake-assistant） ───────────
    reasoning_series: list[str] = []
    for t in all_turns:
        if t.get("role") != "assistant":
            continue
        r = t.get("reasoning")
        if isinstance(r, str) and r.strip():
            reasoning_series.append(r.strip())
    # 末尾 12（与运行期 _reasoning_history[-12:] 等价；运行期 append 顺序 = 上述 ORDER BY 顺序）
    reasoning_series = reasoning_series[-12:]

    # ─ 交错拼装 ──────────────────────────────────────────────────────────
    final: list[dict[str, Any]] = []

    # 1. system（来自 wake.meta_json.system_prompt_text，缺失则 persona_loader 回退）
    stored_sp = meta.get("system_prompt_text")
    if stored_sp and isinstance(stored_sp, str):
        final.append({"role": "system", "content": stored_sp})
    elif persona_loader and meta.get("system_prompt_ref"):
        persona_text = persona_loader(meta["system_prompt_ref"])
        if persona_text:
            final.append({"role": "system", "content": persona_text})

    # 2. continuation_history（来自 wake.meta_json.continuation_history）
    cont = meta.get("continuation_history")
    if isinstance(cont, list):
        for entry in cont:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            if role not in ("user", "assistant", "tool"):
                continue
            m: dict[str, Any] = {"role": role, "content": entry.get("content") or ""}
            name = entry.get("name") or entry.get("tool_name")
            if name:
                m["name"] = name
            if entry.get("tool_call_id"):
                m["tool_call_id"] = entry["tool_call_id"]
            if entry.get("tool_calls"):
                m["tool_calls"] = entry["tool_calls"]
            final.append(m)

    # 3. 交错拼装 turns + injections（详见文档"组装顺序"伪代码）
    # 按 llm_call_seq 分组
    turns_by_call: dict[int, list[dict[str, Any]]] = {}
    for t in all_turns:
        turns_by_call.setdefault(int(t["llm_call_seq"]), []).append(t)

    injs_by_call: dict[int, list[dict[str, Any]]] = {}
    for inj in all_injs:
        injs_by_call.setdefault(int(inj["injected_before_call"]), []).append(inj)

    # (a) apply injections WHERE injected_before_call == 0
    for inj in injs_by_call.get(0, []):
        ai, tl = _injection_as_fake_pair(inj)
        final.append(ai)
        final.append(tl)

    # (b) apply call 0 的 user action prompt（WHERE llm_call_seq==0 AND role=='user'）
    #     ——仅 user；其它 assistant/tool 是 call 0 自己的输出，不进输入。
    #     直接从原始 turns 取，因为对 call_seq==0 的情况，filtered all_turns 是空集
    #     （< 0 是空），但 action prompt 仍需出现在自己的输入里。
    for t in all_turns_raw:
        if int(t["llm_call_seq"]) == 0 and t.get("role") == "user":
            final.append(_turn_to_message(t))
            break  # 一次 call 只有一条 user action prompt（防瞎忙警告在 K>=1 才出现）

    # (c) for k in range(1, call_seq + 1):   # 含 call_seq
    #       apply call (k-1) 的 assistant+tool turns（role != 'user'）作为 k 的输入
    #       apply injections WHERE injected_before_call == k
    for k in range(1, call_seq + 1):
        for t in turns_by_call.get(k - 1, []):
            if t.get("role") == "user":
                # 防瞎忙警告这类 user 归属 (k-1) 的输入侧，不进 k 的输入
                continue
            final.append(_turn_to_message(t))
        for inj in injs_by_call.get(k, []):
            ai, tl = _injection_as_fake_pair(inj)
            final.append(ai)
            final.append(tl)

    # 4. think 注入（provider 守卫保证只 patch 真实历史 assistant）
    provider = resolve_provider(model or "")
    if reasoning_series:
        final = provider.inject_into_messages(final, reasoning_series, max_rounds=10)

    # 5. 压缩暂在 _chat 中外挂（发消息路径），回溯不压缩；后续可归并。
    #    显式说明：final 当前不含压缩后的 narrative 叙事替换；这是文档"按 narrative
    #    存在性判断"段描述的待办，不影响 turns/injections/think 的字面对照。

    return final


__all__ = ["assemble_llm_input"]
