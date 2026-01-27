# Processing Flow Sequence Diagram

```mermaid
sequenceDiagram
    participant GHA as GitHub Actions
    participant M as monitor.py
    participant FC as Firecrawl
    participant OAI as OpenAI
    participant GS as Google Sheets
    participant SL as Slack

    GHA->>M: Trigger daily run (06:00 UTC)

    Note over M: Phase 1: Discovery
    M->>GS: Get seen_urls
    M->>M: Load sources.json (97 sources)

    loop For each source
        M->>FC: map_url / scrape_url
        FC-->>M: Discovered URLs
        M->>GS: Log to discoveries tab
    end

    Note over M: Phase 2: AI Analysis
    alt New URLs found
        loop For each new URL
            M->>FC: scrape_url (with retry)
            FC-->>M: Page content

            M->>OAI: classify_relevance (GPT-4o-mini)
            OAI-->>M: {is_relevant, confidence, category}

            alt Is relevant
                M->>OAI: extract_property_data (GPT-4o)
                OAI-->>M: {title, municipality, summary, confidence}
                M->>GS: Log to proposals tab
            end

            M->>GS: Mark URL as seen
        end
    end

    Note over M: Phase 3: Output
    M->>GS: Log summary to events tab

    alt Proposals found OR failures occurred
        M->>SL: Send notification
    end
```

## Description

This sequence diagram shows the temporal flow of a single monitoring run:

### Trigger
- GitHub Actions triggers the monitor daily at 06:00 UTC
- Can also be triggered manually via workflow_dispatch

### Phase 1: Discovery
1. Load previously seen URLs from Google Sheets
2. Load 97 municipality sources from sources.json
3. For each source:
   - Call Firecrawl `map_url` or `scrape_url` (depending on website type)
   - Log all discovered URLs to `discoveries` tab

### Phase 2: AI Analysis
Only runs if new URLs were discovered:

1. For each new URL:
   - Scrape content with retry logic (max 1 retry)
   - Classify relevance using GPT-4o-mini
   - If relevant: Extract structured data using GPT-4o
   - Log to `proposals` tab if extraction succeeds
   - Mark URL as seen (regardless of outcome)

### Phase 3: Output
1. Log run summary to `events` tab
2. If proposals found OR failures occurred:
   - Send Slack notification with details

### Rate Limiting
- 4.5 seconds between Firecrawl API calls
- 5 seconds retry delay for failed requests

### Error Handling
- All failures logged to `failures` tab
- Failed URLs still marked as seen (prevents retry loops)
- Slack notification includes failure count
