# Firecrawl API Guide (Resights Prototype)

## What Firecrawl Is
Firecrawl is a web data API that converts websites into clean, LLM-ready content.  
It handles dynamic pages, PDFs, proxies, caching, and more, making it suitable for large-scale monitoring of heterogeneous public websites.

This guide focuses on how Resights can use Firecrawl to monitor Danish municipality websites for Grundsalg signals.

---

## Firecrawl CLI & Skill

Firecrawl now ships a CLI plus an installable "Skill" so AI agents (Claude Code, Antigravity, OpenCode, etc.) can run Firecrawl commands directly. This is useful for:

- Quick manual spot-checks of municipalities without wiring new Python
- Verifying a new crawling idea locally before updating `monitor.py`
- Letting Claude Code execute `firecrawl` commands inside workspaces when iterating on prompts or parsing logic

### Documentation Index
- Start from <https://docs.firecrawl.dev/llms.txt> to locate any CLI/agent doc quickly.

### Installation
```bash
npm install -g firecrawl-cli   # global CLI install
npx skills add firecrawl/cli   # optional: add Skill so supported agents auto-configure
```
After installing the Skill, restart Claude Code (or any supported agent) so it discovers Firecrawl.

### Authentication & Status
```bash
firecrawl login                 # interactive login
firecrawl login --browser       # browser-based auth (agent-friendly)
firecrawl login --api-key fc-XXX
export FIRECRAWL_API_KEY=fc-XXX # env var auth
firecrawl config                # view current CLI config
firecrawl --status              # confirm version, auth, credits, concurrency
```

### Core CLI Commands
- `firecrawl <url>` or `firecrawl scrape <url>` — Scrape a single page (`--only-main-content`, `--format markdown,links`, `--wait-for`, screenshots, include/exclude tags, pretty JSON, file output).
- `firecrawl search "query"` — Search the web/news/images with filters (`--limit`, `--sources`, `--categories`, `--tbs`, `--location`, `--scrape`, `--scrape-formats`).
- `firecrawl map <url>` — Discover URLs with filters (`--search`, `--sitemap include|skip|only`, `--include-subdomains`, `--limit`, `--ignore-query-parameters`).
- `firecrawl crawl <url>` — Run async crawls with depth/path/rate controls (`--wait`, `--progress`, `--limit`, `--max-depth`, `--include-paths`, `--delay`, `--max-concurrency`).
- `firecrawl credit-usage` — Inspect credit consumption (`--json --pretty`).
- `firecrawl version` / `--version` — Show CLI version; `--help` / `-h` works for every subcommand. Global `--api-key` overrides stored credentials.

CLI output streams to stdout, so pipe to `head`, `jq`, or `tee` as needed. Multiple formats return JSON; single formats return raw markdown/HTML for easy diffing.

### How We Can Use the CLI
- **Fast validation**: Run `firecrawl map <municipality>` during development to confirm Firecrawl still reaches the sections our automation depends on.
- **Exploratory research**: Use `firecrawl search "grundsalg <region>" --scrape` when onboarding a new municipality to surface candidate URLs before updating `sources.json`.
- **Agent workflows**: Claude Code can call `firecrawl` directly via the Skill when debugging scraping prompts, letting us keep context inside the IDE without switching terminals.
- **Diagnostics**: `firecrawl --status` surfaces concurrency and credit headroom before long runs, which helps planning GitHub Actions usage.

Telemetry is opt-in during auth only (CLI version/OS/tool fingerprint). Disable via `export FIRECRAWL_NO_TELEMETRY=1` if desired.

---

## Authentication

All Firecrawl API requests use Bearer token authentication:

Authorization: Bearer <FIRECRAWL_API_KEY>


---

## Core Concepts

Firecrawl provides multiple endpoints depending on your goal:

- **Map**: discover URLs on a site (fast, cheap, ideal for monitoring)
- **Scrape**: extract clean content from a single page
- **Crawl**: recursively crawl multiple pages (async job)
- **Extract**: structured extraction across multiple URLs
- **Search**: web search + optional scraping

For Grundsalg monitoring, the recommended pattern is:

> Map → Diff → Scrape → LLM → Log → Alert

---

# 1) Map Endpoint — URL Discovery

### Purpose
Discover most URLs on a website and optionally prioritize results using a search query.

This is ideal for daily monitoring because it is fast and lightweight.

### Endpoint
POST https://api.firecrawl.dev/v2/map


### Example Request

```bash
curl -X POST "https://api.firecrawl.dev/v2/map" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.aalborg.dk",
    "search": "grundsalg udbud salg af ejendom byggegrund erhvervsgrund",
    "sitemap": "include",
    "includeSubdomains": true,
    "ignoreQueryParameters": true,
    "limit": 500,
    "timeout": 60000
  }'
Typical Response
{
  "success": true,
  "links": [
    {
      "url": "https://www.aalborg.dk/grundsalg/example",
      "title": "Grundsalg i Aalborg",
      "description": "..."
    }
  ]
}
Recommended Use in Resights
Run daily for each municipality root URL.

Compare returned URLs with seen_urls.

Treat new URLs as candidates for further analysis.

2) Scrape Endpoint — Page Extraction
Purpose
Extract clean content from a single URL in formats such as Markdown, HTML, links, or structured JSON.

Endpoint
POST https://api.firecrawl.dev/v2/scrape
Example Request
curl -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example-municipality.dk/grundsalg/post",
    "formats": ["markdown", "links"],
    "onlyMainContent": true,
    "timeout": 30000
  }'
Typical Response Fields
data.markdown — cleaned page text (best for LLMs)

data.links — outgoing links

data.metadata — title, status code, etc.

Recommended Use in Resights
Run only on URLs detected as new or relevant.

Pass markdown to OpenAI / Gemini for structured extraction.

3) Crawl Endpoint — Deep Crawling (Async)
Purpose
Recursively crawl many pages starting from a root URL.

When to Use
When Map misses relevant pages.

When you need a deeper site traversal.

For initial backfills.

Endpoint
POST https://api.firecrawl.dev/v2/crawl
Example Request
curl -X POST "https://api.firecrawl.dev/v2/crawl" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.aalborg.dk",
    "limit": 200,
    "sitemap": "include",
    "scrapeOptions": {
      "formats": ["markdown", "links"],
      "onlyMainContent": true
    }
  }'
Check Crawl Status
GET https://api.firecrawl.dev/v2/crawl/{crawl_id}
Notes
Crawl is asynchronous.

Results may be chunked/paginated.

Use sparingly in daily monitoring (cost + latency).

4) Extract Endpoint — Structured Extraction
Purpose
Provide URLs + schema/prompt and let Firecrawl extract structured data.

Endpoint
POST https://api.firecrawl.dev/v2/extract
Use Case
Bulk structured extraction.

Alternative to running your own LLM pipeline.

Recommendation for Resights
Prefer:

Scrape → OpenAI/Gemini
for better prompt control and iteration.

5) Search Endpoint — Web Search + Scrape
Purpose
Search the web and optionally scrape results.

Endpoint
POST https://api.firecrawl.dev/v2/search
Use Case
Discover new municipality sources.

Explore unknown domains.

Not required for the core Grundsalg monitoring pipeline.

Recommended Architecture for Grundsalg Monitoring
Daily Pipeline
Map municipality websites (Firecrawl /map)

Diff URLs vs seen_urls

Scrape new URLs (/scrape)

LLM extraction (OpenAI / Gemini)

Log structured results (Google Sheets / DB)

Send notifications (Slack / Email)

Suggested Keyword Set (Danish Grundsalg)
grundsalg
udbud
salg af ejendom
fast ejendom
byggegrund
erhvervsgrund
til salg
budrunde
auktion
matrikel
Practical Tips
Performance
Use /map daily (fast, cheap).

Use /crawl only for difficult sites.

Limit scrape calls with deduplication.

Reliability
Handle HTTP 429 (rate limits) with retries.

Set timeouts.

Log failures per municipality.

Iteration Strategy
Start broad → tighten filters based on false positives.

Resights-Specific Insight
Firecrawl + LLMs enables Resights to transform unstructured municipal content into structured real estate signals.

This project is not only a crawler, but an experiment in building a scalable “Municipal Signal Engine”.
