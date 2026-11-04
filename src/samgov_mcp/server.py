"""SAM.gov Opportunities MCP server.

Two tools, search_opportunities and get_opportunity. Each one runs the Apify actor
cleandatalabs/samgov-opportunities with the user's own APIFY_TOKEN and returns the rows.
Cost: the actor charges $0.003 per returned notice to the token owner's Apify account,
and every call is capped with maxTotalChargeUsd.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
import os
import re
from typing import Annotated, Any, Literal

import httpx
from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__

ACTOR = os.environ.get("SAMGOV_ACTOR", "cleandatalabs~samgov-opportunities").replace("/", "~")
API = "https://api.apify.com/v2"
PRICE_PER_ROW = 0.003
logging.getLogger("httpx").setLevel(logging.WARNING)  # request lines would expose nothing secret, but are noise
HARD_MAX_RESULTS = 200

SET_ASIDES = ["SBA", "SBP", "8A", "8AN", "HZC", "SDVOSBC", "WOSB", "EDWOSB", "VSA", "ISBEE", "IEE", "LAS", "NONE"]
NOTICE_TYPE_CODES = {"Solicitation": "o", "Combined Synopsis/Solicitation": "k", "Presolicitation": "p", "Sources Sought": "r",
                     "Special Notice": "s", "Award Notice": "a", "Justification": "u", "Intent to Bundle": "i",
                     "Sale of Surplus Property": "g"}
NoticeType = Literal["Solicitation", "Combined Synopsis/Solicitation", "Presolicitation", "Sources Sought", "Special Notice",
                     "Award Notice", "Justification", "Intent to Bundle", "Sale of Surplus Property"]

COMPACT_FIELDS = [
    "notice_id", "title", "solicitation_number", "notice_type", "department", "agency", "office", "office_state",
    "posted_date", "modified_date", "response_deadline", "days_until_deadline", "is_active", "naics", "psc_code",
    "set_aside", "set_aside_description", "pop_city", "pop_state", "primary_contact_name", "primary_contact_email",
    "primary_contact_phone", "attachment_count", "award_amount_usd", "award_date", "awardee_name", "awardee_uei",
    "duplicate_of", "url",
]

INSTRUCTIONS = (
    "Search U.S. federal contract opportunities from SAM.gov: solicitations, sources sought, presolicitations and award notices. "
    "Use search_opportunities with filters (NAICS, PSC, set-aside, agency, state, posted since, deadline). Use get_opportunity "
    "for one notice by notice ID, SAM.gov URL or solicitation number. Each returned notice costs $0.003 on the user's Apify account, "
    "so keep max_results small unless the user asks for more."
)

mcp = MCPServer(name="samgov-opportunities", title="SAM.gov Opportunities", version=__version__, instructions=INSTRUCTIONS,
                website_url="https://apify.com/cleandatalabs/samgov-opportunities")


def _token() -> str:
    tok = os.environ.get("APIFY_TOKEN", "").strip()
    if not tok:
        raise ToolError("APIFY_TOKEN is not set. Create a token at https://console.apify.com/settings/integrations "
                        "and add it to this server's env in your MCP client config.")
    return tok


def _build() -> str:
    return os.environ.get("SAMGOV_ACTOR_BUILD", "latest").strip() or "latest"


def _max_charge() -> float:
    try:
        return max(0.003, float(os.environ.get("SAMGOV_MAX_CHARGE_USD", "0.30")))
    except ValueError:
        return 0.30


async def _actor_version(client: httpx.AsyncClient) -> str | None:
    """Build number behind the configured tag (e.g. '0.3.2'), or None if unknown."""
    try:
        r = await client.get(f"{API}/acts/{ACTOR}")
        r.raise_for_status()
        tb = (r.json().get("data") or {}).get("taggedBuilds") or {}
        b = _build()
        if b in tb:
            return tb[b].get("buildNumber")
        return b if re.fullmatch(r"\d+\.\d+(\.\d+)?", b) else None
    except (httpx.HTTPError, ValueError):
        return None


def _ver_tuple(v: str | None) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in (v or "").split("."))
    except ValueError:
        return ()


async def _run_actor(actor_input: dict, max_rows: int) -> list[dict]:
    """Run the actor synchronously and return dataset items. Charge capped to rows*price and SAMGOV_MAX_CHARGE_USD."""
    cap = round(min(_max_charge(), max(1, max_rows) * PRICE_PER_ROW + 0.0005), 4)
    params = {"build": _build(), "maxTotalChargeUsd": cap, "timeout": 290, "clean": "true", "format": "json"}
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {_token()}"}, timeout=httpx.Timeout(310.0)) as client:
        if "lookupIds" in actor_input and _ver_tuple(await _actor_version(client)) < (0, 3):
            raise ToolError("get_opportunity needs actor version 0.3 or newer. Set SAMGOV_ACTOR_BUILD=beta in this server's env "
                            "until 0.3 is the actor's latest build.")
        try:
            r = await client.post(f"{API}/acts/{ACTOR}/run-sync-get-dataset-items", params=params, json=actor_input)
        except httpx.TimeoutException:
            raise ToolError("The actor run took longer than 5 minutes. Narrow the filters or lower max_results.")
        if r.status_code in (401, 403):
            raise ToolError(f"Apify rejected the token (HTTP {r.status_code}). Check APIFY_TOKEN.")
        if r.status_code == 402:
            raise ToolError("Apify says the account has no remaining credit for this run (HTTP 402).")
        if r.status_code >= 400:
            raise ToolError(f"Apify API error HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        return data if isinstance(data, list) else []


def _shape(rows: list[dict], detail: str) -> list[dict]:
    out = []
    for row in rows:
        if row.get("error"):
            out.append({k: row.get(k) for k in ("notice_id", "url", "error")})
        elif detail == "full":
            out.append(row)
        else:
            out.append({k: row[k] for k in COMPACT_FIELDS if row.get(k) not in (None, "", [])})
    return out


def _clean_list(v: list[str] | None) -> list[str]:
    return [s.strip() for s in (v or []) if isinstance(s, str) and s.strip()]


def _days_since(date_str: str) -> int:
    try:
        d = dt.date.fromisoformat(date_str.strip()[:10])
    except ValueError:
        raise ToolError(f"posted_since must be a date like 2026-11-01, got {date_str!r}")
    days = (dt.date.today() - d).days + 1
    if days < 1:
        raise ToolError("posted_since is in the future.")
    return min(days, 365)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True, idempotent_hint=False, destructive_hint=False))
async def search_opportunities(
    keywords: Annotated[str | None, Field(description="Words to search in title and description, e.g. 'roof repair'.")] = None,
    naics_codes: Annotated[list[str] | None, Field(description="NAICS codes or prefixes, e.g. ['541512'] or ['2362', '238'].")] = None,
    psc_codes: Annotated[list[str] | None, Field(description="Product/Service codes or prefixes, e.g. ['DA01'], ['65'], ['Z2'].")] = None,
    set_asides: Annotated[list[str] | None, Field(description="Set-aside codes: SBA (total small business), SBP (partial), 8A, 8AN (8(a) sole source), HZC (HUBZone), "
                                                   "SDVOSBC (service-disabled veteran), WOSB, EDWOSB, VSA (VA veteran-owned), ISBEE, IEE, LAS, or NONE. "
                                                   "Friendly names like 'HUBZone' or 'SDVOSB' also work.")] = None,
    agencies: Annotated[list[str] | None, Field(description="Agency or department names, e.g. ['Department of Veterans Affairs', 'Army'].")] = None,
    states: Annotated[list[str] | None, Field(description="Two-letter place-of-performance states, e.g. ['CO', 'UT'].")] = None,
    notice_types: Annotated[list[NoticeType] | None, Field(description="Only these notice types. Default: all.")] = None,
    posted_since: Annotated[str | None, Field(description="Only notices posted or updated on or after this date (YYYY-MM-DD). Default: last 7 days.")] = None,
    deadline_within_days: Annotated[int | None, Field(ge=1, le=365, description="Only notices whose response deadline is within this many days.")] = None,
    open_for_response_only: Annotated[bool, Field(description="Only notices with a future response deadline (drops awards and notices without a deadline).")] = False,
    max_results: Annotated[int, Field(ge=1, le=HARD_MAX_RESULTS, description="Maximum notices to return. Each costs $0.003.")] = 25,
    detail: Annotated[Literal["compact", "full"], Field(description="'compact' (key fields) or 'full' (description, all contacts, attachment links).")] = "compact",
) -> dict[str, Any]:
    """Search active SAM.gov federal contract opportunities. Returns notices newest first, with agency, deadline, NAICS, PSC,
    set-aside, place of performance, primary contact and SAM.gov link (award notices also include the awardee and amount)."""
    inp: dict[str, Any] = {
        "keywords": (keywords or "").strip(),
        "naicsCodes": _clean_list(naics_codes), "pscCodes": _clean_list(psc_codes),
        "setAsides": [s.upper() if s.upper() in SET_ASIDES else s for s in _clean_list(set_asides)],
        "agencies": _clean_list(agencies), "states": [s.upper() for s in _clean_list(states)],
        "noticeTypes": [NOTICE_TYPE_CODES[t] for t in (notice_types or []) if t in NOTICE_TYPE_CODES],
        "updatedWithinDays": _days_since(posted_since) if posted_since else 7,
        "openForResponseOnly": bool(open_for_response_only), "activeOnly": True,
        "maxResults": int(max_results),
        "includeDetails": True, "includeContacts": True, "includeAttachments": detail == "full",
    }
    if deadline_within_days:
        inp["deadlineWithinDays"] = int(deadline_within_days)
    inp = {k: v for k, v in inp.items() if v not in ("", [])}
    rows = await _run_actor(inp, int(max_results))
    rows = rows[: int(max_results)]
    return {"count": len(rows), "estimated_cost_usd": round(len(rows) * PRICE_PER_ROW, 3),
            "filters": {k: v for k, v in inp.items() if k not in ("includeDetails", "includeContacts", "includeAttachments", "activeOnly")},
            "opportunities": _shape(rows, detail)}


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True, idempotent_hint=True, destructive_hint=False))
async def get_opportunity(
    id: Annotated[str, Field(description="A SAM.gov notice ID (32 hex chars), a sam.gov/opp/... URL, or a solicitation number such as FA813226Q0061.")],
    detail: Annotated[Literal["compact", "full"], Field(description="'full' adds the description, all contacts and attachment links.")] = "full",
) -> dict[str, Any]:
    """Get one SAM.gov opportunity by notice ID, URL or solicitation number. A solicitation number returns all of its
    notices (for example the solicitation, its amendments and the award notice with the winner and amount)."""
    ident = (id or "").strip()
    if not ident:
        raise ToolError("id is required")
    inp = {"lookupIds": [ident], "includeDetails": True, "includeContacts": True, "includeAttachments": detail == "full",
           "maxResults": 20}
    rows = await _run_actor(inp, 20)
    if not rows:
        return {"count": 0, "opportunities": [], "note": f"No SAM.gov notice found for {ident!r}."}
    return {"count": len(rows), "estimated_cost_usd": round(len(rows) * PRICE_PER_ROW, 3), "opportunities": _shape(rows, detail)}


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
