# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kommunal Grundsalg Monitor is a Python-based automated monitoring system that discovers and extracts structured data from Danish municipality websites for property sale announcements ("grundsalg"). It runs daily via GitHub Actions, stores results in Google Sheets, and sends Slack notifications.

**Key Stats:**
- 97 municipality sources monitored
- 5 website type classifications
- Daily automated runs at 06:00 UTC
- Two-stage AI filtering (classification + extraction)

## Quick Start

### Run Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use env.local file)
export FIRECRAWL_API_KEY=<key>
export OPENAI_API_KEY=<key>
export SHEETS_WEBAPP_URL=<url>
export SLACK_WEBHOOK_URL=<url>  # Optional

# Run monitor
python monitor.py
```

### Firecrawl CLI Skill
- Claude Code can run Firecrawl directly via the official CLI/Skill combo. Install globally with `npm install -g firecrawl-cli`, then run `npx skills add firecrawl/cli` inside the Claude environment and restart Claude Code so it registers the new capability. Reference docs live at <https://docs.firecrawl.dev/llms.txt>.
- Use the CLI for ad-hoc `firecrawl map <url>` validations, to run `firecrawl search "grundsalg <municipality>" --scrape` when scouting new sources, or to double-check credits with `firecrawl --status` before long sessions.

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `FIRECRAWL_API_KEY` | Yes | Firecrawl API key for web scraping |
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI classification/extraction |
| `SHEETS_WEBAPP_URL` | Yes | Google Apps Script webhook URL |
| `SLACK_WEBHOOK_URL` | No | Slack Workflow Builder webhook URL |

### GitHub Actions
- **Schedule:** Daily at 06:00 UTC
- **Manual trigger:** workflow_dispatch available
- **Secrets required:** `FIRECRAWL_API_KEY`, `OPENAI_API_KEY`, `SHEETS_WEBAPP_URL`, `SLACK_WEBHOOK_URL`

## Feature Development Workflow

**CRITICAL: When starting ANY new feature or non-trivial implementation, you MUST use the AskUserQuestion tool to conduct an in-depth requirements discovery session BEFORE writing any code.**

### Requirements Discovery Process

1. **Always Start with AskUserQuestion**
   - Do NOT make assumptions about implementation details
   - Do NOT skip to coding based on a brief request
   - Use AskUserQuestion to gather comprehensive requirements

2. **Interview Depth & Coverage**

   Ask probing questions across ALL relevant dimensions:

   **Technical Implementation:**
   - What existing systems/patterns should this integrate with?
   - Are there performance constraints or scalability concerns?
   - What data persistence strategy makes sense?
   - Should this be synchronous or asynchronous?
   - What error handling and recovery mechanisms are needed?
   - Are there backward compatibility requirements?
   - What logging/monitoring should be included?

   **Architecture & Design:**
   - Where should this live in the codebase?
   - Should this be a new module or extend existing functionality?
   - What abstraction level is appropriate?
   - Are there reusability considerations?
   - How should this interact with the current pipeline?
   - What dependencies should we introduce (if any)?

   **User Experience & Interface:**
   - Who will interact with this feature? (end users, developers, CI/CD)
   - What does success look like from a UX perspective?
   - Should there be configuration options? How exposed?
   - What feedback/output should users see?
   - Are there accessibility considerations?

   **Data & State:**
   - What data needs to be stored, and where?
   - What's the data lifecycle (creation, updates, deletion)?
   - Are there privacy or data retention concerns?
   - Should data be cached? For how long?
   - What happens to existing data?

   **Edge Cases & Failure Modes:**
   - What could go wrong?
   - How should the system behave during failures?
   - What are the rollback strategies?
   - Are there race conditions to consider?
   - What validation is needed?

   **Tradeoffs & Alternatives:**
   - What are the alternative approaches?
   - What are the pros/cons of each?
   - What are we optimizing for? (speed, cost, reliability, maintainability)
   - What technical debt might this introduce?
   - What's the migration path if we need to change this later?

   **Cost & Resource Impact:**
   - Will this increase API costs? By how much?
   - What's the computational cost?
   - Does this affect rate limits?
   - Are there storage implications?

   **Testing & Validation:**
   - How will we test this?
   - What does "done" look like?
   - Are there metrics to track?
   - What manual testing is needed?

3. **Question Quality Guidelines**

   **DO:**
   - Ask about non-obvious tradeoffs
   - Explore "why" behind the request
   - Present informed options with context
   - Ask follow-up questions based on previous answers
   - Challenge assumptions constructively
   - Ask about constraints and requirements

   **DON'T:**
   - Ask obvious questions like "Should I write tests?" (always yes)
   - Ask permission to do standard practices
   - Present false dichotomies
   - Ask questions you can infer from codebase context
   - Ask the same question in different words

4. **Iterative Discovery**
   - Use AskUserQuestion multiple times
   - Each answer should inform the next question
   - Continue until you have a complete mental model
   - Don't rush to implementation

5. **Specification Document**

   After gathering requirements, write a comprehensive spec to a file (e.g., `specs/feature-name.md`):

   ```markdown
   # Feature: [Name]

   ## Overview
   [Brief description and motivation]

   ## Requirements
   ### Functional
   - [Specific requirement 1]
   - [Specific requirement 2]

   ### Non-Functional
   - Performance: [targets]
   - Cost: [budget]
   - Reliability: [SLA]

   ## Technical Design
   ### Architecture
   [Component diagram or description]

   ### Data Model
   [Schema changes, new fields, etc.]

   ### API/Interface
   [New functions, parameters, returns]

   ## Implementation Plan
   1. [Step 1]
   2. [Step 2]

   ## Tradeoffs & Decisions
   - Decision: [Choice made]
     - Alternatives considered: [A, B, C]
     - Rationale: [Why this choice]

   ## Testing Strategy
   - Unit tests: [Coverage areas]
   - Integration tests: [Scenarios]
   - Manual testing: [Steps]

   ## Risks & Mitigations
   - Risk: [Potential issue]
     - Mitigation: [How to handle]

   ## Cost Impact
   [Estimated costs from API usage, storage, etc.]

   ## Rollout Plan
   [How to deploy, rollback strategy]
   ```

6. **Get Final Approval**
   - Present the spec to the user
   - Use AskUserQuestion one final time to confirm the approach
   - Only after approval, proceed to implementation

### Example Session Flow

```
User: "I want to add email notifications"

❌ WRONG:
Claude: I'll add email notifications using SendGrid...
[starts coding]

✅ CORRECT:
Claude: I'll gather requirements for the email notification feature.
[Uses AskUserQuestion with 3-4 questions about:]
- Who should receive emails? (admins, property owners, subscribers?)
- When should emails be sent? (every discovery, daily digest, on-demand?)
- What email service constraints exist? (cost, volume limits, deliverability)
- How should we handle failures and retries?

[User answers]

Claude: Based on your answers, I have follow-up questions...
[Uses AskUserQuestion again with 2-3 questions about:]
- Should emails be templated? What information should they contain?
- Do we need unsubscribe functionality?
- What about rate limiting to avoid spam flags?

[User answers]

Claude: Let me confirm the technical approach...
[Uses AskUserQuestion to present 2-3 architecture options:]
- Option A: Integrate SendGrid directly
- Option B: Use Slack webhooks to forward to email
- Option C: Google Apps Script email forwarding
Each with pros/cons

[User selects approach]

Claude: I'll now write a specification document.
[Writes detailed spec to specs/email-notifications.md]

Claude: I've created the specification. Please review...
[Uses AskUserQuestion for final approval]

[User approves]

Claude: Starting implementation...
```

### When to Skip This Process

Only skip the detailed AskUserQuestion workflow for:
- Trivial bug fixes (typos, obvious errors)
- Explicit user instructions with all details provided
- Maintenance tasks (dependency updates, etc.)
- Documentation-only changes

For everything else, **ALWAYS** conduct thorough requirements discovery.

## Architecture

### Processing Pipeline
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: DISCOVERY                              │
│  sources.json → discover_new_urls() → Firecrawl map/scrape              │
│  Output: Raw URLs logged to 'discoveries' tab                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 2: AI ANALYSIS                               │
│  (Only runs if new URLs found)                                          │
│  scrape_with_retry() → classify_relevance() → extract_property_data()   │
│  Output: Relevant listings to 'proposals' tab, failures to 'failures'   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                       PHASE 3: OUTPUT                                   │
│  Summary → 'events' tab                                                 │
│  Slack notification (if proposals found OR failures occurred)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Files

| File | Purpose |
|------|---------|
| `monitor.py` | Main orchestration script (~556 lines) |
| `sheets.py` | Google Sheets API wrapper |
| `sources.json` | 97 municipality sources with type classification |
| `requirements.txt` | Python dependencies |
| `.github/workflows/daily-monitor.yml` | GitHub Actions workflow |
| `apps-script.gs` | Google Apps Script for Sheets webhook |

### Key Functions in monitor.py

| Function | Purpose | API Used |
|----------|---------|----------|
| `get_sources()` | Load municipality URLs from sources.json | - |
| `get_existing_urls()` | Load seen URLs for deduplication | Google Sheets |
| `discover_new_urls()` | Find new property listing URLs | Firecrawl map/scrape |
| `scrape_with_retry()` | Scrape URL with retry logic | Firecrawl scrape |
| `classify_relevance()` | Classify if content is property-related | OpenAI GPT-4o-mini |
| `extract_property_data()` | Extract structured data from listing | OpenAI GPT-4o |
| `send_slack_notification()` | Send notification to Slack | Slack webhook |
| `log_failure()` | Log failures to Google Sheets | Google Sheets |

### Website Type Classification

Sources are classified into 5 types with different discovery strategies:

| Type | Count | Strategy | Example |
|------|-------|----------|---------|
| `dedicated_portal` | 15 | map_url with keywords | grundsalg.aarhus.dk |
| `kortinfo` | 10 | scrape_url (JS SPA workaround) | grundsalg.kortinfo.net |
| `news_feed` | 5 | map_url + AI classification | frederiksberg.dk/nyheder |
| `municipality_subsection` | 65 | map_url with keywords | koege.dk/.../byggegrunde |
| `minimal` | 2 | scrape base URL only | gentofte.dk |

### Google Sheets Structure

| Tab | Purpose | Columns |
|-----|---------|---------|
| `discoveries` | Raw Firecrawl findings | timestamp, source_id, source_name, url, source_type |
| `proposals` | AI-analyzed listings | timestamp, municipality, title, url, confidence, summary |
| `seen_urls` | Deduplication tracking | url, timestamp |
| `events` | System logs/heartbeat | timestamp, type, title, description, ... |
| `failures` | Error tracking | timestamp, url, source_id, failure_type, error_message |

## Cost Estimates

### Monthly Operating Costs

| Service | Low Estimate | High Estimate |
|---------|--------------|---------------|
| Firecrawl (Standard plan) | $83 | $83 |
| OpenAI | $20 | $60 |
| Google Sheets | Free | Free |
| Slack | Free | Free |
| GitHub Actions | Free | Free |
| **Total** | **~$103/mo** | **~$143/mo** |

### Per-Run Breakdown

| Operation | API | Est. Calls | Cost |
|-----------|-----|------------|------|
| Discovery (map_url) | Firecrawl | 97 | ~97 credits |
| Scraping (scrape_url) | Firecrawl | 50-500 | ~50-500 credits |
| Classification | OpenAI GPT-4o-mini | 200 | ~$0.10 |
| Extraction | OpenAI GPT-4o | 50 | ~$1.21 |

### Cost Optimization Tips

1. **Two-stage filtering already implemented** - Saves ~80% on extraction costs
2. **Reduce map_url limits** - Lower DISCOVERY_CONFIG limits if too many URLs
3. **Skip stable sources** - Some municipalities rarely update
4. **Batch AI calls** - Process multiple pages per API call (future optimization)

## Technical Details

### Rate Limiting
```python
RATE_LIMIT_DELAY = 4.5  # seconds between Firecrawl API calls
RETRY_DELAY = 5         # seconds before retry
MAX_RETRIES = 1         # number of retries for transient failures
```

### AI Models Used
- **Classification:** GPT-4o-mini (cheap, fast) - ~$0.15/1M input tokens
- **Extraction:** GPT-4o (accurate) - ~$2.50/1M input tokens

### Error Handling
- Retry logic for transient Firecrawl failures
- All failures logged to `failures` tab
- Slack notification includes failure count
- Failed URLs still marked as "seen" to prevent retry loops

## Common Tasks

### Add a New Municipality Source
1. Edit `sources.json`
2. Add entry with: `id`, `name`, `url`, `region`, `type`
3. Choose appropriate `type` based on website structure

### Test Slack Notification
```python
python3 -c "
from monitor import send_slack_notification
send_slack_notification('Test message', [{'municipality': 'Test', 'title': 'Test', 'url': 'https://test.dk', 'confidence': 0.9}])
"
```

### Check Classification Logic
```python
python3 -c "
from monitor import classify_relevance
print(classify_relevance('https://example.dk/grundsalg', 'Parcelhusgrund til salg...'))
"
```

### Manual Trigger via GitHub Actions
1. Go to Actions tab in GitHub
2. Select "Daily Grundsalg Monitor"
3. Click "Run workflow"

## Troubleshooting

### "Insufficient credits" from Firecrawl
- Check Firecrawl dashboard for credit balance
- Upgrade plan if needed (Standard: 100k credits/mo)

### No new URLs discovered
- Normal if sources haven't updated
- Check `seen_urls` tab - URLs are only processed once

### Slack notification not received
- Verify `SLACK_WEBHOOK_URL` is set correctly
- Check Slack Workflow Builder is published
- Look for "Slack notification sent successfully" in logs

### Classification marking everything as irrelevant
- Check `classify_relevance()` keyword list
- Verify content is being scraped correctly
- Review AI classification prompt

## Related Documentation

- [PROJECT_HISTORY.md](PROJECT_HISTORY.md) - Development history and decisions
- [README.md](README.md) - User-facing documentation
- [prd.md](prd.md) - Original product requirements
