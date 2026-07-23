"""把对外发送的超长文本切分成单条消息上限内的段。

各通道（飞书/微信 ClawBot/微信 OA）对单条文本消息有字符上限——超长会被
平台拒绝或被静默截断。这里提供统一的贪心切分：在不超过 max_length 的前提下，
优先按段落 → 换行 → 句末标点聚合，最后用硬切兜底，保证进度。

设计约束：
- 切分单位是字符（不是字节）。当前三通道上限 ≥ 2000 字符，远小于
  UTF-8 编码后的字节风险阈值，字符数足够安全。
- 不做 overlap（保持简单，避免重复发送同一段内容）。
- 不修改文本内容（不加尾标记、不加段号）；段标记由调用方在 UX 层决定，
  本函数保持纯函数性质便于复用与测试。
"""

from __future__ import annotations

# 句末标点：在找不到换行时退而求其次，在句末断开。中英均覆盖。
# 不含逗号/分号——在逗号处断开读感太差。
_SENTENCE_ENDS = "。！？!?…\n"


def split_text_for_send(text: str, max_length: int) -> list[str]:
    """把 text 切成不超过 ``max_length`` 字符的段。

    Args:
        text: 待切分的原始文本。允许空串。
        max_length: 每段字符上限。必须 >= 1，否则按 1 兜底（保证单字符也能发）。

    Returns:
        非空 list[str]。空串返回 ``[""]``——调用方自行决定空文本是否发送。
        每段长度 <= max_length。段拼接后 == text（无字符丢失）。
    """
    if max_length < 1:
        max_length = 1
    if not text:
        return [""]
    if len(text) <= max_length:
        return [text]

    segments: list[str] = []
    pos = 0
    n = len(text)
    while pos < n:
        end = pos + max_length
        if end >= n:
            # 剩余整段放得下
            segments.append(text[pos:])
            break

        window = text[pos:end]
        # 优先在换行/段落边界（最大的 \n）切，其次句末标点
        cut = _find_break(window)
        if cut <= 0:
            # 窗口内找不到任何可断点（极罕见，如连续无标点长串）
            # → 硬切在 max_length 处，保证进度
            segments.append(window)
            pos = end
        else:
            # 在 cut（含切分字符本身，把换行/标点留在前段末尾）后断
            segments.append(text[pos : pos + cut])
            pos += cut
    return segments


def _find_break(window: str) -> int:
    """在 window 内找一个合适的切分点（返回切分字符的结束偏移，1-based 风格）。

    优先级：
      1. 最后一个 ``\\n``（含段落 ``\\n\\n``）——读感最好
      2. 最后一个句末标点（。！？!?…）
    返回的偏移是「切分字符之前所有字符长度 + 切分字符本身」，
    即返回值 k 表示「window[:k] 作为一段，window[k:] 继续聚合」。
    找不到任何可断点返回 0。
    """
    # 1. 换行（自动覆盖段落 \n\n，因为按最后一个 \n 切即可）
    last_nl = window.rfind("\n")
    if last_nl >= 0:
        return last_nl + 1
    # 2. 句末标点
    for ch in reversed(_SENTENCE_ENDS):
        # _SENTENCE_ENDS 含 \n，但已被上面覆盖；这里查其他标点
        if ch == "\n":
            continue
        idx = window.rfind(ch)
        if idx >= 0:
            return idx + 1
    return 0
