# SAM.gov Opportunities MCP server

<!-- mcp-name: io.github.CleanDataLabs/samgov-opportunities -->

This MCP server lets an AI assistant (Claude Desktop, Cursor, VS Code, Claude Code or any other MCP client) search U.S. federal contract opportunities on SAM.gov: solicitations, sources sought, presolicitations and award notices.

Each call runs the Apify actor [cleandatalabs/samgov-opportunities](https://apify.com/cleandatalabs/samgov-opportunities) under **your own Apify token**. You don't need a SAM.gov API key and there is no 10-requests-per-day limit.

## Tools

| Tool | What it does |
|---|---|
| `search_opportunities` | Searches active notices, newest first. Filters: `keywords`, `naics_codes`, `psc_codes` (both accept prefixes, e.g. `2362` or `Z2`), `set_asides` (SBA, 8A, HZC, SDVOSBC, WOSB, EDWOSB and others), `agencies` (by name), `states` (place of performance), `notice_types`, `posted_since` (YYYY-MM-DD, posted or updated on or after that date; default is the last 7 days), `deadline_within_days`, `open_for_response_only`, `max_results` (default 25, max 200) and `detail` (`compact` or `full`). |
| `get_opportunity` | Fetches one notice by notice ID, `sam.gov/opp/...` URL or solicitation number. A solicitation number returns all of its notices, including the award (winner, UEI, amount). |

Compact rows include the notice ID, title, solicitation number, type, department, agency and office, posted and deadline dates, NAICS, PSC, set-aside, place of performance, primary contact, attachment count, award fields and the SAM.gov link. `detail: "full"` adds the description, all contacts and attachment links.

Both tools are read-only.

## Cost

The actor charges **$0.003 per returned notice** (25 results cost $0.075), billed to the Apify account that owns the token. Apify's free plan includes $5 of monthly credit. Each tool call carries a spending cap: the lower of `max_results × $0.003` and `SAMGOV_MAX_CHARGE_USD` (default `$0.30`). Each result reports `estimated_cost_usd`.

## Install

You need [uv](https://docs.astral.sh/uv/) (for `uvx`), or Python 3.10+ with pip, and an Apify API token from [Console > Settings > API & Integrations](https://console.apify.com/settings/integrations).

### Claude Desktop / Cursor / any client with an `mcpServers` config

```json
{
  "mcpServers": {
    "samgov": {
      "command": "uvx",
      "args": ["samgov-opportunities-mcp"],
      "env": { "APIFY_TOKEN": "apify_api_..." }
    }
  }
}
```

### Claude Code

```bash
claude mcp add samgov --env APIFY_TOKEN=apify_api_... -- uvx samgov-opportunities-mcp
```

### VS Code (`.vscode/mcp.json`)

```json
{
  "inputs": [{ "type": "promptString", "id": "apify-token", "description": "Apify API token", "password": true }],
  "servers": {
    "samgov": { "type": "stdio", "command": "uvx", "args": ["samgov-opportunities-mcp"],
                "env": { "APIFY_TOKEN": "${input:apify-token}" } }
  }
}
```

### From source

```bash
git clone https://github.com/CleanDataLabs/samgov-opportunities-mcp && cd samgov-opportunities-mcp
pip install -e .
APIFY_TOKEN=apify_api_... samgov-opportunities-mcp   # speaks MCP over stdio
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `APIFY_TOKEN` | (required) | Your Apify API token. Runs are billed to this account. |
| `SAMGOV_MAX_CHARGE_USD` | `0.30` | Spending cap per tool call. |
| `SAMGOV_ACTOR_BUILD` | `latest` | Actor build tag or number to run. `get_opportunity` needs actor 0.3 or newer. |

## Example prompts

- "Find small-business set-aside janitorial contracts in Colorado posted this week."
- "Any VA construction solicitations under NAICS 2362 due in the next 30 days?"
- "Who won solicitation FA813226Q0061, and for how much?"
- "Show me HUBZone IT services opportunities (NAICS 5415) from the Army since 2026-11-01."

## No-install alternative: Apify's hosted MCP server

To skip installing anything, point your client at Apify's hosted server and limit it to this actor:

```json
{ "mcpServers": { "samgov": { "url": "https://mcp.apify.com/?tools=cleandatalabs/samgov-opportunities" } } }
```

It signs you in with OAuth, or you can send `Authorization: Bearer <APIFY_TOKEN>`. It exposes the actor as one generic tool with every raw actor input, plus run and dataset helper tools. This package instead offers two focused tools with typed filters, compact output and a per-call spending cap.

## Development

```bash
pip install -e ".[test]"
pytest                                  # offline tests over a real MCP stdio session
SAMGOV_LIVE=1 APIFY_TOKEN=... pytest    # adds a live search + get (about $0.01)
npx @modelcontextprotocol/inspector -e APIFY_TOKEN=... -- samgov-opportunities-mcp
```

## Data source and disclaimer

The data comes from public SAM.gov notices. This project is not affiliated with or endorsed by the U.S. General Services Administration or SAM.gov. Always confirm deadlines and requirements on the official notice before you bid.

## License

MIT
