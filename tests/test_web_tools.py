"""web_search / web_fetch 工具测试。

不依赖真实外网——用 monkeypatch 打桩 HTTP 客户端与 DNS，覆盖：
  - 工具注册与 toolset 归属（所有实例默认可用）
  - 参数校验（缺 query/url、非法 scheme、limit 边界）
  - SSRF 防护（拒绝私网/环回/元数据/非 http(s)）
  - DuckDuckGo HTML 解析（标题/URL/摘要配对 + uddg 解码）
  - HTML → 纯文本抽取（去 script、保留段落、提 title）
  - web_fetch 成功路径（HTML 转文本 + 截断标记）
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest


@pytest.fixture(autouse=True)
def _import_web_tools() -> None:
    """确保 web 工具已注册（fresh process 也成立）。"""
    import interfaces.tools.web_tools  # noqa: F401


def _dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    from interfaces.tools.registry import registry

    return json.loads(registry.dispatch(name, args))


# ── 注册与归属 ──

def test_web_tools_registered_in_web_toolset():
    from interfaces.tools.registry import registry

    assert registry.get_toolset_for_tool("web_search") == "web"
    assert registry.get_toolset_for_tool("web_fetch") == "web"
    defs = registry.get_definitions({"web_search", "web_fetch"})
    names = {d["function"]["name"] for d in defs}
    assert names == {"web_search", "web_fetch"}


def test_web_tools_listed_in_toolset_catalog():
    from interfaces.tools.toolsets import TOOLSETS

    web = TOOLSETS.get("web")
    assert web is not None
    assert set(web["tools"]) == {"web_search", "web_fetch"}


def test_web_toolset_available_in_both_wake_kinds():
    from domain.lifecycle.wake import L4_TASK_TOOLSETS, L4_TOOLSETS

    assert "web" in L4_TOOLSETS
    assert "web" in L4_TASK_TOOLSETS


# ── 参数校验 ──

def test_web_search_requires_query():
    out = _dispatch("web_search", {})
    assert "error" in out


def test_web_fetch_requires_url():
    out = _dispatch("web_fetch", {})
    assert "error" in out


def test_web_fetch_rejects_non_http_scheme():
    out = _dispatch("web_fetch", {"url": "ftp://example.com/x"})
    assert "error" in out


def test_web_search_limit_clamped(monkeypatch):
    # 打桩免费后端，返回空，避免触网
    monkeypatch.setattr(
        "interfaces.tools.web_tools._bing_search", lambda q, l: []
    )
    monkeypatch.setattr(
        "interfaces.tools.web_tools._ddg_search", lambda q, l: []
    )
    out = _dispatch("web_search", {"query": "x", "limit": 999})
    assert out["count"] == 0
    # limit 超上限不报错，正常返回


# ── SSRF 防护 ──

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/x",
    "http://localhost/x",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/x",
    "http://192.168.1.1/x",
    "http://[::1]/x",
])
def test_web_fetch_blocks_private_targets(url):
    out = _dispatch("web_fetch", {"url": url})
    assert "error" in out
    assert "SSRF" in out["error"] or "非公网" in out["error"]


def test_web_fetch_blocks_metadata_hostname(monkeypatch):
    # metadata.google.internal 会解析到 169.254.169.254，被 IP 检查拦下
    out = _dispatch("web_fetch", {"url": "http://metadata.google.internal/"})
    assert "error" in out


def test_web_fetch_allow_private_env_override(monkeypatch):
    monkeypatch.setenv("WEB_FETCH_ALLOW_PRIVATE", "1")
    # 打桩实际请求，避免触网——重点验证 SSRF 门被 env 跳过
    captured: dict[str, Any] = {}

    class _FakeResp:
        status_code = 200
        headers = {"content-type": "text/plain"}
        text = "ok"
        url = "http://127.0.0.1/x"

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            captured["called"] = True
            return _FakeResp()

    monkeypatch.setattr("interfaces.tools.web_tools.httpx.Client", _FakeClient)
    out = _dispatch("web_fetch", {"url": "http://127.0.0.1/x"})
    assert captured.get("called") is True
    assert out.get("text") == "ok"


# ── DuckDuckGo 解析 ──

_DDG_HTML = """
<html><body>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=x">Example Page</a>
  <a class="result__snippet">An example snippet here</a>
</div>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fanthropic.com">Second Title</a>
  <a class="result__snippet">second snippet</a>
</div>
<script>var x=1;</script>
</body></html>
"""


def test_ddg_parser_pairs_results():
    from interfaces.tools.web_tools import _DDGResultParser

    p = _DDGResultParser()
    p.feed(_DDG_HTML)
    p.close()
    results = p.results(10)
    assert len(results) == 2
    assert results[0] == {
        "title": "Example Page",
        "url": "https://example.com/a",
        "snippet": "An example snippet here",
    }
    assert results[1]["url"] == "https://anthropic.com"
    assert results[1]["title"] == "Second Title"


def test_ddg_parser_respects_limit():
    from interfaces.tools.web_tools import _DDGResultParser

    p = _DDGResultParser()
    p.feed(_DDG_HTML)
    p.close()
    assert len(p.results(1)) == 1


def test_decode_ddg_href_passthrough_and_redirect():
    from interfaces.tools.web_tools import _decode_ddg_href

    assert _decode_ddg_href("https://foo.com/bar") == "https://foo.com/bar"
    assert _decode_ddg_href("") == ""
    assert (
        _decode_ddg_href("//duckduckgo.com/l/?uddg=https%3A%2F%2Fbar.com%2Fp")
        == "https://bar.com/p"
    )


# ── HTML → 文本 ──

def test_html_to_text_strips_script_and_extracts_title():
    from interfaces.tools.web_tools import _html_to_text

    html = (
        "<html><head><title>My Page</title></head>"
        "<body><h1>Hi</h1><p>Para one</p>"
        "<script>bad()</script><p>Para two</p></body></html>"
    )
    title, text = _html_to_text(html)
    assert title == "My Page"
    assert "bad" not in text
    assert "Para one" in text
    assert "Para two" in text


# ── web_fetch 成功路径（打桩 httpx） ──

def _stub_httpx(monkeypatch, *, body: str, content_type: str = "text/html", status: int = 200):
    class _FakeResp:
        status_code = status
        headers = {"content-type": content_type}
        text = body
        url = "https://example.com/page"

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            return _FakeResp()

    monkeypatch.setattr("interfaces.tools.web_tools.httpx.Client", _FakeClient)


def test_web_fetch_converts_html_to_text(monkeypatch):
    _stub_httpx(
        monkeypatch,
        body="<html><head><title>Example</title></head><body><p>Hello world</p></body></html>",
    )
    out = _dispatch("web_fetch", {"url": "https://example.com/page", "max_length": 5000})
    assert out["status_code"] == 200
    assert out["title"] == "Example"
    assert "Hello world" in out["text"]
    assert out["truncated"] is False


def test_web_fetch_truncates_long_text(monkeypatch):
    _stub_httpx(monkeypatch, body="<html><body><p>" + ("A" * 10_000) + "</p></body></html>")
    out = _dispatch("web_fetch", {"url": "https://example.com/page", "max_length": 1000})
    assert out["truncated"] is True
    assert out["length"] == 1000


def test_web_search_uses_bing_by_default(monkeypatch):
    calls: dict[str, Any] = {}

    def fake_bing(query, limit):
        calls["query"] = query
        calls["limit"] = limit
        return [{"title": "T", "url": "https://x.com", "snippet": "S"}]

    monkeypatch.setattr("interfaces.tools.web_tools._bing_search", fake_bing)
    out = _dispatch("web_search", {"query": "hello", "limit": 3})
    assert calls == {"query": "hello", "limit": 3}
    assert out["provider"] == "bing"
    assert out["count"] == 1
    assert out["results"][0]["url"] == "https://x.com"


def test_web_search_uses_tavily_when_configured(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "tavily")
    monkeypatch.setenv("WEB_SEARCH_API_KEY", "sk-test")

    def fake_tavily(query, limit):
        return [{"title": "Tav", "url": "https://tav.com", "snippet": "TavS"}]

    monkeypatch.setattr("interfaces.tools.web_tools._tavily_search", fake_tavily)
    out = _dispatch("web_search", {"query": "hello"})
    assert out["provider"] == "tavily"
    assert out["results"][0]["url"] == "https://tav.com"


def test_web_search_tavily_without_key_falls_back(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "tavily")
    monkeypatch.delenv("WEB_SEARCH_API_KEY", raising=False)

    monkeypatch.setattr(
        "interfaces.tools.web_tools._tavily_search", lambda q, l: []
    )
    # bing 也返回空，最终落到 ddg
    monkeypatch.setattr(
        "interfaces.tools.web_tools._bing_search", lambda q, l: []
    )
    monkeypatch.setattr(
        "interfaces.tools.web_tools._ddg_search",
        lambda q, l: [{"title": "DDG", "url": "https://ddg.com", "snippet": ""}],
    )
    out = _dispatch("web_search", {"query": "hello"})
    assert "fallback" in out["provider"]
    assert out["count"] == 1


def test_web_search_bing_falls_back_to_ddg(monkeypatch):
    # 默认 bing 返回空 → 自动 fallback 到 ddg
    monkeypatch.setattr(
        "interfaces.tools.web_tools._bing_search", lambda q, l: []
    )
    monkeypatch.setattr(
        "interfaces.tools.web_tools._ddg_search",
        lambda q, l: [{"title": "DDG", "url": "https://ddg.com", "snippet": "s"}],
    )
    out = _dispatch("web_search", {"query": "hello"})
    assert out["provider"] == "duckduckgo (fallback)"
    assert out["count"] == 1


def test_bing_parser_pairs_results():
    from interfaces.tools.web_tools import _BingResultParser

    html = """
    <html><body>
    <li class="b_algo">
      <h2 class=""><a target="_blank" href="https://example.com/a" h="ID=SERP,1.1">Example <strong>Page</strong></a></h2>
      <div class="b_caption"><p>An example snippet here</p></div>
    </li>
    <li class="b_algo">
      <h2><a href="https://anthropic.com">Second Title</a></h2>
      <div class="b_caption"><p>second snippet</p></div>
    </li>
    <script>var x=1;</script>
    </body></html>
    """
    p = _BingResultParser()
    p.feed(html)
    p.close()
    results = p.results(10)
    assert len(results) == 2
    assert results[0] == {
        "title": "Example Page",
        "url": "https://example.com/a",
        "snippet": "An example snippet here",
    }
    assert results[1]["url"] == "https://anthropic.com"
    assert results[1]["title"] == "Second Title"


def test_bing_parser_respects_limit():
    from interfaces.tools.web_tools import _BingResultParser

    html = (
        '<li class="b_algo"><h2><a href="https://a.com">A</a></h2>'
        '<div class="b_caption"><p>s1</p></div></li>'
        '<li class="b_algo"><h2><a href="https://b.com">B</a></h2>'
        '<div class="b_caption"><p>s2</p></div></li>'
    )
    p = _BingResultParser()
    p.feed(html)
    p.close()
    assert len(p.results(1)) == 1


# ── 工具加载清单 ──

def test_web_tools_in_agent_load_list():
    import inspect
    from infrastructure.ai import agent as agent_mod

    src = inspect.getsource(agent_mod.AIAgent._ensure_tools_loaded)
    assert "interfaces.tools.web_tools" in src
