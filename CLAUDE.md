# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kommunal Grundsalg Monitor is a Python-based automated monitoring system that discovers and extracts structured data from Danish municipality websites for property sale announcements ("grundsalg"). It runs daily via GitHub Actions and stores results in Google Sheets.

## Commands

### Run locally
```bash
pip install -r requirements.txt
export SHEETS_WEBAPP_URL=<url>
export FIRECRAWL_API_KEY=<key>
export OPENAI_API_KEY=<key>
python monitor.py
```

### GitHub Actions
- Runs automatically daily at 06:00 UTC
- Can be triggered manually via workflow_dispatch
- Secrets required: `SHEETS_WEBAPP_URL`, `FIRECRAWL_API_KEY`, `OPENAI_API_KEY`

## Architecture

### Data Flow
```
sources (Google Sheet) → monitor.py → Firecrawl discovery → OpenAI extraction → events/seen_urls (Google Sheets)
```

### Core Components

**monitor.py** - Main orchestration script:
1. `get_sources()` - Loads municipal website URLs from 'sources' sheet
2. `get_existing_urls()` - Loads already-processed URLs from 'seen_urls' sheet for deduplication
3. `discover_new_urls()` - Uses Firecrawl's `map()` with keyword search to find property listing pages
4. `extract_property_data()` - Scrapes URLs with Firecrawl, then uses GPT-4o to extract structured fields (municipality, title, description, price, deadline, address)
5. `main()` - Orchestrates the pipeline and logs heartbeat summaries

**sheets.py** - Google Sheets wrapper using custom webapp endpoint (not direct API):
- `append_row(sheet_name, row)` - Appends data row
- `get_rows(sheet_name)` - Reads all rows

### Google Sheets Structure
- **sources** - Municipality URLs to monitor (column 1 = URL)
- **seen_urls** - Processed URLs for deduplication (columns: url, timestamp)
- **events** - Discovered listings and system events (columns: timestamp, municipality, title, address, price, deadline, url, event_type)

### Key Technical Details
- Firecrawl search keywords: "grundsalg parcelhusgrunde erhvervsudstykning ejendomme til salg"
- Map limit: 50 URLs per source
- Graceful degradation: skips Firecrawl/OpenAI steps if API keys not set
- Always logs heartbeat event (even on failure) for monitoring
