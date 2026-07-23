"""Web tools — 让数字生命联网搜索与阅读。

提供两个工具，注册到 ``web`` 工具集：
  - ``web_search``：联网搜索，返回标题/URL/摘要列表。
  - ``web_fetch`` ：抓取单个 URL，把 HTML 转成可读纯文本。

设计取舍：
  - 不引入新依赖——用已有的 ``httpx``（同步）+ 标准库 ``html.parser``。
  - ``web_search`` 默认走 **Bing** HTML 端点：国内/全球均可访问，无需 API key，
    所有实例开箱即用。DuckDuckGo 在中国大陆网络不可达，仅作可选后端
    （``WEB_SEARCH_PROVIDER=duckduckgo``）。配 ``WEB_SEARCH_PROVIDER=tavily``
    与 ``WEB_SEARCH_API_KEY`` 可改走 Tavily。主后端返回 0 结果时自动 fallback
    到下一个免费后端，提升网络环境差异下的可用性。
  - ``web_fetch`` 内置 SSRF 防护：拒绝抓取私网/环回/链路本地/元数据地址，
    避免 agent 被 prompt 注入诱导访问内网。可用 ``WEB_FETCH_ALLOW_PRIVATE=1``
    在受控开发环境关闭该限制。
  - 工具不消耗精力（与 terminal_tool 一致），保持网络能力与精力解耦。
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from interfaces.tools.registry import registry

logger = logging.getLogger(__name__)

# ── 超时：联网工具不能让一次坏请求卡死整个 wake ──
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

MAX_SEARCH_RESULTS = 10
DEFAULT_FETCH_LENGTH = 20_000


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


# ───────────────────────── SSRF 防护 ─────────────────────────

_METADATA_HOSTS = frozenset({
    "169.254.169.254",        # AWS / GCP / Azure 元数据
    "metadata.google.internal",
    "metadata.azure.com",
})


def _host_is_public(host: str) -> bool:
    """解析 host，仅当所有解析地址都是公网地址才放行。

    host 可能是域名或 IP 字面量。私网/环回/链路本地/保留/组播地址一律拒绝。
    """
    if not host:
        return False
    if host.lower() in _METADATA_HOSTS:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        # 只要有一个地址落在非公网段就拒绝（覆盖 DNS rebinding 的混合解析）
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def _assert_fetchable_url(url: str) -> tuple[str, str]:
    """校验 URL 合法且目标可抓取，返回 (scheme, host)。不合法抛 ValueError。"""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"只支持 http/https，收到: {scheme or '(空)'}")
    if not host:
        raise ValueError("URL 缺少 host")
    if os.getenv("WEB_FETCH_ALLOW_PRIVATE", "").strip() not in ("1", "true", "True"):
        if not _host_is_public(host):
            raise ValueError(f"目标地址非公网，已拒绝（SSRF 防护）: {host}")
    return scheme, host


# ───────────────────────── HTML → 文本 ─────────────────────────

_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "br", "caption", "div", "dl",
    "dt", "dd", "fieldset", "figcaption", "figure", "footer", "h1", "h2", "h3",
    "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
    "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
})
_SCRIPT_STYLE = frozenset({"script", "style", "noscript", "template"})


class _TitleAndTextExtractor(HTMLParser):
    """同时抽取标题与正文的提取器（替代上面 _in_title 的启发式）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._title_depth = 0
        self._title_buf: list[str] = []
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE:
            self._skip_depth += 1
            return
        if tag == "title":
            self._title_depth += 1
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "title" and self._title_depth > 0:
            self._title_depth -= 1
            title = "".join(self._title_buf).strip()
            if title and not self.title:
                self.title = title
            self._title_buf = []
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._title_depth:
            self._title_buf.append(data)
            return
        if data:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [ln.strip() for ln in raw.splitlines()]
        out: list[str] = []
        for ln in lines:
            if not ln:
                if out and out[-1]:
                    out.append("")
                continue
            out.append(ln)
        return "\n".join(out).strip()


def _html_to_text(html: str) -> tuple[str, str]:
    """返回 (title, text)。"""
    extractor = _TitleAndTextExtractor()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:
        logger.debug("HTML 解析失败，回退为原始文本", exc_info=True)
    return extractor.title, extractor.text()


# ───────────────────────── web_search ─────────────────────────

class _BingResultParser(HTMLParser):
    """解析 Bing 结果页，按文档顺序收集标题/URL 与摘要。

    Bing 结构：每个 ``<li class="b_algo">`` 含
    ``<h2><a href="URL">标题</a></h2>`` 与 ``<div class="b_caption">...<p>摘要</p>``。
    URL 为直链，无需解码。标题里的 ``<strong>`` 高亮由 handle_data 自然合并。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._titles: list[tuple[str, str]] = []  # (title, url)
        self._snippets: list[str] = []
        self._h2_depth = 0
        self._a_in_h2 = False
        self._cur_url = ""
        self._title_buf: list[str] = []
        self._caption_depth = 0
        self._cap_p = False
        self._cap_buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE:
            self._skip_depth += 1
            return
        attrd = {k.lower(): (v or "") for k, v in attrs}
        if tag == "h2":
            self._h2_depth += 1
            return
        if tag == "a" and self._h2_depth and not self._a_in_h2:
            self._a_in_h2 = True
            self._cur_url = attrd.get("href", "")
            return
        if tag == "div" and "b_caption" in attrd.get("class", ""):
            self._caption_depth += 1
            return
        if tag == "p" and self._caption_depth and not self._cap_p:
            self._cap_p = True
            self._cap_buf = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "a" and self._a_in_h2:
            title = "".join(self._title_buf).strip()
            if title or self._cur_url:
                self._titles.append((title, self._cur_url))
            self._a_in_h2 = False
            self._cur_url = ""
            self._title_buf = []
            return
        if tag == "h2" and self._h2_depth:
            self._h2_depth -= 1
            return
        if tag == "p" and self._cap_p:
            text = "".join(self._cap_buf).strip()
            if text:
                self._snippets.append(text)
            self._cap_p = False
            self._cap_buf = []
            return
        if tag == "div" and self._caption_depth:
            self._caption_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._a_in_h2:
            self._title_buf.append(data)
        elif self._cap_p:
            self._cap_buf.append(data)

    def results(self, limit: int) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        n = min(len(self._titles), limit)
        for i in range(n):
            title, url = self._titles[i]
            snippet = self._snippets[i] if i < len(self._snippets) else ""
            if not url:
                continue
            out.append({
                "title": title or "(无标题)",
                "url": url,
                "snippet": snippet,
            })
        return out


def _bing_search(query: str, limit: int) -> list[dict[str, str]]:
    """Bing HTML 端点搜索（无需 key，国内/全球可达）。"""
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(
                "https://www.bing.com/search",
                params={"q": query, "count": str(max(limit, 10))},
                headers={**_BROWSER_HEADERS, "Accept": "text/html"},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("web_search Bing 请求失败: %s", exc)
        return []
    parser = _BingResultParser()
    try:
        parser.feed(resp.text)
        parser.close()
    except Exception:
        logger.debug("Bing 结果解析失败", exc_info=True)
    return parser.results(limit)


class _DDGResultParser(HTMLParser):
    """解析 DuckDuckGo HTML 结果页，按文档顺序收集标题/URL 与摘要。

    DDG html 端点结构：每个结果含 ``<a class="result__a" href="...uddg=...">标题</a>``
    与 ``<a class="result__snippet">摘要</a>``。真实 URL 编码在 href 的 uddg 参数里。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._titles: list[tuple[str, str]] = []  # (title, url)
        self._snippets: list[str] = []
        self._cur_kind: str | None = None  # 'a' | 'snippet' | None
        self._cur_url = ""
        self._cur_buf: list[str] = []
        self._skip_depth = 0

    def _flush(self) -> None:
        if self._cur_kind is None:
            return
        text = "".join(self._cur_buf).strip()
        if self._cur_kind == "a":
            if text or self._cur_url:
                self._titles.append((text, self._cur_url))
        elif self._cur_kind == "snippet":
            if text:
                self._snippets.append(text)
        self._cur_kind = None
        self._cur_url = ""
        self._cur_buf = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE:
            self._skip_depth += 1
            return
        if tag != "a":
            return
        attrd = {k.lower(): (v or "") for k, v in attrs}
        cls = attrd.get("class", "")
        if "result__a" in cls:
            self._flush()
            self._cur_kind = "a"
            self._cur_url = _decode_ddg_href(attrd.get("href", ""))
        elif "result__snippet" in cls:
            self._flush()
            self._cur_kind = "snippet"

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SCRIPT_STYLE and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "a" and self._cur_kind is not None:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._cur_kind is None:
            return
        self._cur_buf.append(data)

    def results(self, limit: int) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        n = min(len(self._titles), limit)
        for i in range(n):
            title, url = self._titles[i]
            snippet = self._snippets[i] if i < len(self._snippets) else ""
            if not url:
                continue
            out.append({
                "title": title or "(无标题)",
                "url": url,
                "snippet": snippet,
            })
        return out


def _decode_ddg_href(href: str) -> str:
    """从 DDG 跳转链接里解出真实 URL；非跳转链接原样返回。"""
    if not href:
        return ""
    # DDG 的 l/?uddg=<encoded> 跳转
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return unquote(qs["uddg"][0])
    # 相对协议 //host/...
    if href.startswith("//"):
        return "https:" + href
    return href


def _ddg_search(query: str, limit: int) -> list[dict[str, str]]:
    """DuckDuckGo HTML 端点搜索（无需 key）。"""
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": "wt-wt"},
                headers={**_BROWSER_HEADERS, "Accept": "text/html"},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("web_search DuckDuckGo 请求失败: %s", exc)
        return []
    parser = _DDGResultParser()
    try:
        parser.feed(resp.text)
        parser.close()
    except Exception:
        logger.debug("DDG 结果解析失败", exc_info=True)
    return parser.results(limit)


def _tavily_search(query: str, limit: int) -> list[dict[str, str]]:
    """Tavily 搜索 API（需 WEB_SEARCH_API_KEY）。"""
    api_key = os.getenv("WEB_SEARCH_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": limit,
                    "search_depth": "basic",
                },
                headers=_BROWSER_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("web_search Tavily 请求失败: %s", exc)
        return []
    out: list[dict[str, str]] = []
    for item in data.get("results", []) or []:
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        out.append({
            "title": str(item.get("title") or "(无标题)"),
            "url": url,
            "snippet": str(item.get("content") or "").strip(),
        })
    return out[:limit]


def _resolve_search_provider() -> str:
    return os.getenv("WEB_SEARCH_PROVIDER", "bing").strip().lower()


# 免费后端 fallback 顺序：主后端 0 结果时依次尝试，直到拿到结果或穷尽。
# Bing 国内可达，DDG 仅海外可达——两者互补，覆盖不同部署网络。
_FREE_FALLBACK = ["bing", "duckduckgo"]


def _run_search(provider: str, query: str, limit: int) -> list[dict[str, str]]:
    if provider == "tavily":
        return _tavily_search(query, limit)
    if provider == "duckduckgo":
        return _ddg_search(query, limit)
    return _bing_search(query, limit)


def _handle_web_search(args: dict[str, Any], **_: Any) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        return registry.tool_error("query is required")
    limit = args.get("limit")
    try:
        limit = int(limit) if limit is not None else 5
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))

    provider = _resolve_search_provider()
    results = _run_search(provider, query, limit)

    # 主后端 0 结果 → 按免费 fallback 链补试（跳过已试过的）
    used = {provider}
    if not results:
        for fb in _FREE_FALLBACK:
            if fb in used:
                continue
            results = _run_search(fb, query, limit)
            used.add(fb)
            if results:
                provider = f"{fb} (fallback)"
                break

    return _j({
        "query": query,
        "provider": provider,
        "count": len(results),
        "results": results,
        "note": (
            "用 web_fetch 阅读某条结果的完整内容。"
            if results
            else "未找到结果，可换关键词重试。"
        ),
    })


# ───────────────────────── web_fetch ─────────────────────────

def _handle_web_fetch(args: dict[str, Any], **_: Any) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        return registry.tool_error("url is required")
    try:
        _assert_fetchable_url(url)
    except ValueError as exc:
        return registry.tool_error(str(exc))

    raw_format = str(args.get("format") or "text").strip().lower()
    want_html = raw_format == "html"
    try:
        max_length = int(args.get("max_length") or DEFAULT_FETCH_LENGTH)
    except (TypeError, ValueError):
        max_length = DEFAULT_FETCH_LENGTH
    max_length = max(500, min(max_length, 50_000))

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers=_BROWSER_HEADERS)
            final_url = str(resp.url)
            content_type = resp.headers.get("content-type", "")
            status_code = resp.status_code
            # 非文本响应不解析，避免把二进制塞进上下文
            body = resp.text if _is_text_content(content_type) else ""
    except httpx.HTTPError as exc:
        return registry.tool_error(f"抓取失败: {type(exc).__name__}: {exc}")

    title = ""
    text = body
    if body and not want_html:
        is_html = "html" in content_type.lower() or "<html" in body[:2000].lower()
        if is_html:
            title, text = _html_to_text(body)
        # 非文本或纯文本：直接用 body

    truncated = False
    if len(text) > max_length:
        text = text[:max_length]
        truncated = True

    return _j({
        "url": url,
        "final_url": final_url,
        "status_code": status_code,
        "content_type": content_type,
        "title": title,
        "text": text,
        "truncated": truncated,
        "length": len(text),
    })


def _is_text_content(content_type: str) -> bool:
    ct = content_type.lower()
    if not ct:
        return True  # 未知类型，尝试当文本读
    return any(tok in ct for tok in ("text", "html", "json", "xml", "javascript"))


# ───────────────────────── 注册 ─────────────────────────

registry.register(
    name="web_search",
    toolset="web",
    schema={
        "name": "web_search",
        "description": (
            "联网搜索：用关键词查询网页，返回标题、URL 与摘要列表。"
            "适合查最新信息、事实核对、找资料。默认用 Bing（国内/全球可达），"
            "拿到结果后用 web_fetch 阅读完整页面。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限，默认 5，最多 10",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        },
    },
    handler=_handle_web_search,
    check_fn=lambda: True,
    emoji="🔍",
)

registry.register(
    name="web_fetch",
    toolset="web",
    schema={
        "name": "web_fetch",
        "description": (
            "抓取并阅读一个网页 URL 的内容，返回可读纯文本（自动去标签）。"
            "用于阅读 web_search 找到的页面，或直接获取某网址内容。"
            "仅支持 http/https，且目标必须是公网地址。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要抓取的网页 URL（http/https）"},
                "max_length": {
                    "type": "integer",
                    "description": "返回文本的最大字符数，默认 20000，上限 50000",
                    "minimum": 500,
                    "maximum": 50000,
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "html"],
                    "description": "text=纯文本（默认），html=原始 HTML",
                },
            },
            "required": ["url"],
        },
    },
    handler=_handle_web_fetch,
    check_fn=lambda: True,
    emoji="🌐",
    max_result_size_chars=24_000,
)
