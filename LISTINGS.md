# Listing drafts: SAM.gov Opportunities MCP server

Nothing below has been submitted. Every step needs Alex's own accounts: GitHub, PyPI, and Glama/mcp.so sign-in.
Drafted 2026-11-04 (MST). Requirements were checked on that date.

## 0. Prerequisites (in this order)

1. **Pick the GitHub owner.** These files assume the GitHub org **`CleanDataLabs`** (it exists, was created 2026-08-25 and has 0 public repos; confirm it's yours).
   If you publish under another account, replace `CleanDataLabs` in `server.json` (`name`, `repository.url`), `README.md` (the `mcp-name` comment, clone URL) and `pyproject.toml` (`[project.urls]`).
   The registry name must stay `io.github.<GitHubLogin>/...`, and the `mcp-name:` line in README.md must match `server.json` `name` exactly.
2. **Create the public repo** `CleanDataLabs/samgov-opportunities-mcp` and push this folder. `.venv/`, `dist/` and caches are git-ignored. A local git repo with one commit is ready:
   ```bash
   cd /workspace/apify/samgov-mcp
   git remote add origin git@github.com:CleanDataLabs/samgov-opportunities-mcp.git
   git push -u origin main
   ```
3. **Set your GitHub username** in `glama.json` (`"maintainers": ["<your-github-username>"]`). Glama needs this for org-owned repos.
4. **Publish to PyPI** (the name `samgov-opportunities-mcp` was free on 2026-11-04):
   ```bash
   python -m build && twine upload dist/*     # needs a PyPI account + API token
   ```
   Then check that `uvx samgov-opportunities-mcp` starts. The README goes into the PyPI description and carries the
   `mcp-name: io.github.CleanDataLabs/samgov-opportunities` line that the Official Registry uses to verify you own the package.
5. *(Recommended, not required)* Promote actor 0.3 to `latest`. Until then, `get_opportunity` returns a clear error unless the user sets `SAMGOV_ACTOR_BUILD=beta`. `search_opportunities` already works on 0.2.2 (tested).

---

## 1. Official MCP Registry (registry.modelcontextprotocol.io)

- **Cost**: free. **Review**: none (automated validation). It's in preview, so data resets are possible.
- **Requirements**: the package is live on PyPI with the `mcp-name` line in its README; `description` is at most 100 chars (ours is 95); the namespace `io.github.<login>` is proven by GitHub login.
- **File**: `server.json` in this folder. It validates against the `2025-12-11` schema (checked locally with jsonschema).

| Field | Value |
|---|---|
| name | `io.github.CleanDataLabs/samgov-opportunities` |
| title | `SAM.gov Opportunities` |
| description | `Search SAM.gov federal contract opportunities by NAICS, PSC, set-aside, agency, state and date.` |
| version | `0.1.0` |
| repository | `https://github.com/CleanDataLabs/samgov-opportunities-mcp` (github) |
| websiteUrl | `https://apify.com/cleandatalabs/samgov-opportunities` |
| package | pypi `samgov-opportunities-mcp` 0.1.0, runtimeHint `uvx`, transport stdio |
| env vars | `APIFY_TOKEN` (required, secret), `SAMGOV_MAX_CHARGE_USD` (optional, default 0.30), `SAMGOV_ACTOR_BUILD` (optional, default latest) |

**Steps for Alex**
```bash
# install the publisher CLI (macOS/Linux)
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
./mcp-publisher login github        # device-code login as the GitHub account/org member that owns CleanDataLabs
./mcp-publisher publish             # run in this folder; reads server.json
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.CleanDataLabs/samgov-opportunities"
```
For a new version, bump `version` in `pyproject.toml`, `src/samgov_mcp/__init__.py` and both places in `server.json`, upload to PyPI, then publish again.
The GitHub MCP Registry (github.com/mcp) reads from the Official Registry but adds servers by manual curation, so listing there is optional and a separate step.


---

## 2. Glama (glama.ai/mcp/servers)

- **Cost**: free. **Requirements**: a public GitHub repo; `glama.json` with your GitHub username (needed to claim an org repo); a build that starts and answers `initialize` + `tools/list` without credentials (verified locally: the server starts and lists both tools with no token).
- **Steps**
  1. Sign in to glama.ai with GitHub, then **Add Server** and enter `https://github.com/CleanDataLabs/samgov-opportunities-mcp`. Glama may also find it automatically through the Official Registry.
  2. On the server page, open **Score**, then **Claim ownership** (Glama reads `glama.json`).
  3. Go to `https://glama.ai/mcp/servers/CleanDataLabs/samgov-opportunities-mcp/admin/dockerfile` and fill in the form:

| Field | Value |
|---|---|
| Base image | default (`debian:trixie-slim`) |
| Python version | `3.12` |
| Build steps | `["pip install ."]` (or `["uv pip install --system ."]`) |
| CMD arguments | `["samgov-opportunities-mcp"]` |
| Environment variables JSON schema | `{"type":"object","properties":{"APIFY_TOKEN":{"type":"string","description":"Apify API token; runs bill $0.003 per notice to this account"},"SAMGOV_MAX_CHARGE_USD":{"type":"string","default":"0.30"},"SAMGOV_ACTOR_BUILD":{"type":"string","default":"latest"}},"required":["APIFY_TOKEN"]}` |
| Placeholder parameters | `{"APIFY_TOKEN":"placeholder"}` (the scanner only lists tools, so no real token is needed) |

  4. Click **Deploy** (build test), then **Make Release**: version `0.1.0`, changelog "Initial release: search_opportunities, get_opportunity."
  5. Add these in the admin UI, which has no repo fields for them:
     - Categories: *Search / Data / Finance / Government*.
     - Short description: the same text as the Registry.
     - Related servers (optional).
     - Run **Try in Browser** once, which seeds usage for the score.

A plain `Dockerfile` is also in the repo for `docker run -i --rm -e APIFY_TOKEN=... samgov-opportunities-mcp`. Glama generates its own Dockerfile from the form.

---

## 3. Smithery (smithery.ai): **not possible any more**

On 2026-10-31 Smithery shut down accounts, API keys, the CLI/SDKs and its publishing flow (source: smithery.ai/future; `smithery.ai/new` now returns 404). smithery.ai stays online as a curated directory powered by Arcade, and it has no submission route. **Alex doesn't need to do anything.** If a way to submit comes back, use the Registry text above. Don't add `smithery.yaml`, because nothing reads it now.

---

## 4. mcp.so

As of 2026-11-04 there are two routes:

**A. The web form at https://mcp.so/submit, which costs $39.** The form shows only a paid card ("$39 one-time publishing fee": publish without review, verified badge, featured placement, dofollow link). It needs sign-in and Alex's own card. Fields:

| Field | Value |
|---|---|
| Tab | MCP Server |
| Repository URL* | `https://github.com/CleanDataLabs/samgov-opportunities-mcp` |
| Name | `SAM.gov Opportunities` |

**B. A free GitHub issue on `chatmcp/mcpso`.** It's community-reviewed, has no stated turnaround, and the repo has thousands of open issues. Draft:

- **Title**: `Submit: SAM.gov Opportunities MCP server`
- **Body**:
  ```
  Name: SAM.gov Opportunities
  Repository: https://github.com/CleanDataLabs/samgov-opportunities-mcp
  Package: uvx samgov-opportunities-mcp (PyPI)

  Description: Search U.S. federal contract opportunities from SAM.gov from any MCP client. Two read-only tools:
  search_opportunities (keywords, NAICS and PSC prefixes, set-asides such as 8(a)/HUBZone/SDVOSB/WOSB, agency, state,
  notice type, posted-since date, deadline window) and get_opportunity (by notice ID, SAM.gov URL or solicitation number,
  including award winner and amount). No SAM.gov API key needed; runs on the user's own Apify token at $0.003 per notice,
  with a per-call spending cap.

  Tags: government, sam.gov, federal-contracts, govcon, procurement, search
  Category: Search / Data
  Install (Claude Code): claude mcp add samgov --env APIFY_TOKEN=apify_api_... -- uvx samgov-opportunities-mcp
  ```

---

## 5. Already live, nothing to submit: Apify's hosted MCP

`https://mcp.apify.com/?tools=cleandatalabs/samgov-opportunities` works today (tested 2026-11-04). It offers one generic tool, `cleandatalabs--samgov-opportunities`, with every raw actor input (a 16 KB schema), plus run and dataset helper tools. Sign-in is OAuth or an Apify token. The README mentions it as the no-install option. That URL belongs to Apify, so don't list it under our name in the registries.

## Checklist for Alex

- [ ] Confirm or replace the GitHub owner `CleanDataLabs`; put your username in `glama.json`
- [ ] Create the public GitHub repo and push
- [ ] Upload to PyPI (`twine upload dist/*`)
- [ ] `mcp-publisher login github` then `mcp-publisher publish`
- [ ] Glama: add, claim, fill the Dockerfile form, deploy, release
- [ ] mcp.so: pay $39 on the form, or open the free GitHub issue drafted above
- [ ] Smithery: nothing (closed)
- [ ] Optional: promote actor 0.3 to `latest` so `get_opportunity` works without `SAMGOV_ACTOR_BUILD=beta`
