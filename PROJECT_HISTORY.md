# Project History: Kommunal Grundsalg Monitor

This document chronicles the development journey of the Kommunal Grundsalg Monitor, a system designed to automatically discover and extract property sale announcements from Danish municipality websites.

---

## Phase 1: Initial Setup & Infrastructure

### Problem Statement
Resights researchers were manually monitoring ~50+ Danish municipality websites every 3-4 weeks for property sale announcements ("grundsalg"). This process:
- Required ~10 hours/month of manual work
- Had delays of up to 3-4 weeks in discovering announcements
- Was error-prone and not scalable

### Decisions Made
1. **Tech Stack Selection**
   - Python for main logic (simplicity, good library support)
   - GitHub Actions for scheduling (free tier, no infrastructure to manage)
   - Google Sheets for data storage (easy to view, no database setup needed)
   - Firecrawl for web scraping (handles JavaScript rendering, provides API)
   - OpenAI GPT-4o for data extraction (best accuracy for Danish text)

2. **Architecture**
   - Serverless approach via GitHub Actions
   - Apps Script webhook for Google Sheets (avoids OAuth complexity)
   - Local `sources.json` file for municipality URLs (version controlled)

### Files Created
- `monitor.py` - Main orchestration script
- `sheets.py` - Google Sheets API wrapper
- `requirements.txt` - Python dependencies
- `.github/workflows/daily-monitor.yml` - GitHub Actions workflow
- `apps-script.gs` - Google Apps Script for Sheets webhook

---

## Phase 2: Multi-Type Website Discovery

### Challenge Discovered
Danish municipality websites have **5 distinct structures** requiring different scraping strategies:

| Type | Example | Count | Challenge |
|------|---------|-------|-----------|
| Dedicated Portal | grundsalg.aarhus.dk | 15 | Well-structured, easy |
| Kortinfo.net | grundsalg.kortinfo.net/* | 10 | JavaScript SPA, map_url returns 0 |
| News Feed | frederiksberg.dk/nyheder | 5 | Mixed content, needs filtering |
| Municipality Subsection | koege.dk/.../byggegrunde | 65 | Standard pages |
| Minimal/Archived | gentofte.dk | 2 | Rarely updated |

### Decisions Made
1. **Type Classification** - Added `type` field to each source in `sources.json`
2. **Type-Specific Discovery**
   - Dedicated portals: Use `map_url` with property keywords
   - Kortinfo: Use `scrape_url` with link extraction (workaround for JS SPAs)
   - News feeds: Use `map_url` + AI classification to filter irrelevant pages
   - Subsections: Standard `map_url` with property keywords
   - Minimal: Only scrape base URL

3. **Discovery Configuration**
   ```python
   DISCOVERY_CONFIG = {
       "dedicated_portal": {"limit": 100, "keywords": "villagrunde storparceller"},
       "kortinfo": {"limit": 100, "keywords": "parcelhusgrunde boliggrunde"},
       "news_feed": {"limit": 20, "keywords": "grundsalg byggegrunde", "classify": True},
       "municipality_subsection": {"limit": 50, "keywords": "grundsalg parcelhusgrunde"},
       "minimal": {"limit": 5, "keywords": "grundsalg ejendomme"},
   }
   ```

### Results
- Successfully classified all 97 municipality sources
- First full run discovered 521 URLs

---

## Phase 3: Relevance Analysis & Filtering

### Challenge Discovered
The 521 discovered URLs included significant noise:
- Generic municipality pages
- News articles about housing policy (not actual sales)
- PDF links, sitemaps, contact pages

### Decisions Made
1. **Two-Stage Filtering**
   - Stage 1: Classification with GPT-4o-mini (cheap, fast) - ~$0.15/1M tokens
   - Stage 2: Extraction with GPT-4o (accurate) - ~$2.50/1M tokens
   - Only run expensive extraction on relevant pages

2. **Filter Level: LOOSE**
   - Include anything potentially property-related
   - Only exclude clearly irrelevant pages (contact, cookies, etc.)
   - Prioritize coverage over precision

3. **Two-Tab Google Sheets Structure**
   - `discoveries` - Raw Firecrawl findings (audit trail)
   - `proposals` - AI-analyzed listings (actionable data)

### Implementation
Created `classify_relevance()` function with:
- Keyword matching first (fast, free)
- AI classification for ambiguous cases
- Structured response: `{is_relevant, confidence, category, reason}`

### Cost Savings
- Before: 521 URLs × GPT-4o = ~$2-5 per run
- After: 521 URLs × GPT-4o-mini + ~100 × GPT-4o = ~$1.30 per run
- **~80% cost reduction**

---

## Phase 4: Simplified Output & Slack Notifications

### User Requirement
- Don't need complex 14-column extraction
- Just need high confidence that property listing was identified
- Want Slack notification when new proposals are found

### Decisions Made
1. **Simplified Extraction Prompt**
   ```json
   {
     "is_property_listing": boolean,
     "confidence": 0.0-1.0,
     "title": string,
     "municipality": string,
     "summary": string
   }
   ```

2. **Slack Integration via Workflow Builder**
   - No Slack app needed (requires paid Slack plan)
   - Simple webhook trigger
   - Sends: `message`, `proposals_count`, `details`

3. **Simplified Proposals Tab**
   - 6 columns: timestamp, municipality, title, url, confidence, summary
   - Down from 14 columns

### Implementation
- Added `send_slack_notification()` function
- Payload structured for Slack Workflow Builder
- Added `SLACK_WEBHOOK_URL` to GitHub Actions secrets

---

## Phase 5: Reliability Monitoring & Failure Tracking

### Challenge Discovered
Failures were **silent**:
- Failed URLs skipped without record
- No way to know if URL failed vs. wasn't relevant
- Slack only notified on success
- No retry logic for transient failures

### Decisions Made
1. **Comprehensive Stats Tracking**
   ```python
   stats = {
       "sources_processed": 0,
       "urls_discovered": 0,
       "urls_attempted": 0,
       "scrape_success": 0,
       "scrape_failed": [],
       "classification_success": 0,
       "classification_failed": [],
       "extraction_success": 0,
       "extraction_failed": [],
       "proposals_created": 0,
       "skipped_irrelevant": 0,
   }
   ```

2. **Retry Logic**
   - 1 retry for transient failures
   - 5-second delay between retries
   - 4.5-second rate limit between Firecrawl calls

3. **Failure Logging**
   - New `failures` tab in Google Sheets
   - Columns: timestamp, url, source_id, failure_type, error_message
   - Failure types: `scrape_failed`, `classification_failed`, `extraction_failed`

4. **Enhanced Slack Notifications**
   - Triggered on proposals OR failures
   - Shows failure count in header
   - Lists first 5 failed URLs in details

### Implementation
- Added `scrape_with_retry()` function
- Added `log_failure()` function
- Updated `main()` with comprehensive stats tracking
- Updated heartbeat summary with detailed breakdown

---

## Current System Architecture

### Processing Pipeline
```
1. DISCOVERY PHASE
   sources.json → discover_new_urls() → Firecrawl map/scrape → discoveries tab

2. AI ANALYSIS PHASE (only if new URLs found)
   discoveries → scrape_with_retry() → classify_relevance() → extract_property_data()

3. OUTPUT PHASE
   relevant listings → proposals tab
   failures → failures tab
   summary → events tab + Slack notification
```

### File Structure
```
kommunal-grundsalg-monitor/
├── monitor.py           # Main orchestration (556 lines)
├── sheets.py            # Google Sheets wrapper
├── sources.json         # 97 municipality sources with type classification
├── requirements.txt     # Python dependencies
├── env.local            # Local environment variables (not committed)
├── .github/
│   └── workflows/
│       └── daily-monitor.yml    # GitHub Actions workflow
└── apps-script.gs       # Google Apps Script for Sheets webhook
```

### Google Sheets Structure
| Tab | Purpose | Columns |
|-----|---------|---------|
| discoveries | Raw Firecrawl findings | timestamp, source_id, source_name, url, source_type |
| proposals | AI-analyzed listings | timestamp, municipality, title, url, confidence, summary |
| seen_urls | Deduplication | url, timestamp |
| events | System logs/heartbeat | timestamp, type, title, description, ... |
| failures | Error tracking | timestamp, url, source_id, failure_type, error_message |

---

## Key Learnings

### Technical
1. **Firecrawl map_url fails on JavaScript SPAs** - Kortinfo sites needed scrape_url workaround
2. **Two-stage AI filtering is cost-effective** - 80% cost reduction with GPT-4o-mini classification
3. **Rate limiting is critical** - 4.5s delay prevents Firecrawl API errors
4. **Retry logic handles transient failures** - Many "failures" are temporary

### Product
1. **Loose filtering > strict filtering** - Better to review false positives than miss real listings
2. **Simple output beats complex extraction** - Users just need to know "is this a listing?"
3. **Failure visibility is essential** - Silent failures erode trust in automation

### Process
1. **Iterative development works** - Each phase built on learnings from previous
2. **Start simple, add complexity** - Initial 14-column extraction was overkill
3. **Validate assumptions early** - First run revealed website type diversity

---

## Future Considerations

### Potential Optimizations
1. **Reduce Firecrawl calls** - Cache results, skip unchanged sources
2. **Batch AI calls** - Process multiple pages in single API call
3. **Smart scheduling** - More frequent checks for active sources

### Possible Extensions
1. **Email notifications** - Alternative to Slack
2. **Dashboard** - Visual monitoring of system health
3. **Historical analysis** - Track listing trends over time
4. **Additional signal types** - Zoning changes, planning applications

---

## Timeline Summary

| Phase | Focus | Key Outcome |
|-------|-------|-------------|
| 1 | Infrastructure | GitHub Actions + Google Sheets pipeline |
| 2 | Discovery | 97 sources classified, 5 type-specific strategies |
| 3 | Filtering | Two-stage AI classification, 80% cost reduction |
| 4 | Notifications | Slack integration, simplified output |
| 5 | Reliability | Failure tracking, retry logic, comprehensive stats |

---

*Last updated: January 2026*
