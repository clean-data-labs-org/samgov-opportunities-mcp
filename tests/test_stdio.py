"""End-to-end test through a real MCP stdio client.
Offline checks always run. Live checks run only with APIFY_TOKEN and SAMGOV_LIVE=1 (cost about $0.02)."""
import json
import os
import sys

import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

LIVE = bool(os.environ.get("APIFY_TOKEN")) and os.environ.get("SAMGOV_LIVE") == "1"


def params(**env):
    base = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "APIFY_TOKEN")}
    base.update(env)
    return StdioServerParameters(command=sys.executable, args=["-m", "samgov_mcp"], env=base)


def payload(res):
    if getattr(res, "structured_content", None):
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


async def _session(env, fn):
    async with stdio_client(params(**env)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return await fn(s)


@pytest.mark.asyncio
async def test_lists_tools():
    async def fn(s):
        return (await s.list_tools()).tools
    tools = {t.name: t for t in await _session({}, fn)}
    assert set(tools) == {"search_opportunities", "get_opportunity"}
    props = tools["search_opportunities"].input_schema["properties"]
    for k in ("naics_codes", "set_asides", "agencies", "states", "posted_since", "max_results"):
        assert k in props
    assert tools["get_opportunity"].annotations.read_only_hint


@pytest.mark.asyncio
async def test_missing_token_is_tool_error():
    async def fn(s):
        return await s.call_tool("search_opportunities", {"max_results": 1})
    res = await _session({"APIFY_TOKEN": ""}, fn)
    assert res.is_error and "APIFY_TOKEN" in res.content[0].text


@pytest.mark.asyncio
async def test_bad_date_is_tool_error():
    async def fn(s):
        return await s.call_tool("search_opportunities", {"posted_since": "last week", "max_results": 1})
    res = await _session({"APIFY_TOKEN": "x"}, fn)
    assert res.is_error and "posted_since" in res.content[0].text


@pytest.mark.skipif(not LIVE, reason="set SAMGOV_LIVE=1 and APIFY_TOKEN")
@pytest.mark.asyncio
async def test_live_search_and_get():
    env = {"SAMGOV_ACTOR_BUILD": os.environ.get("SAMGOV_ACTOR_BUILD", "beta"), "SAMGOV_MAX_CHARGE_USD": "0.03"}

    async def fn(s):
        a = await s.call_tool("search_opportunities", {"naics_codes": ["561720"], "set_asides": ["SBA"], "states": [],
                                                       "max_results": 2})
        sr = payload(a)
        nid = sr["opportunities"][0]["notice_id"]
        b = await s.call_tool("get_opportunity", {"id": f"https://sam.gov/opp/{nid}/view", "detail": "compact"})
        return a, sr, b, payload(b), nid
    a, sr, b, gr, nid = await _session(env, fn)
    assert not a.is_error and 1 <= sr["count"] <= 2
    assert all("561720" in o["naics"] for o in sr["opportunities"])
    assert not b.is_error and gr["opportunities"][0]["notice_id"] == nid
