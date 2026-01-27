# System Architecture Flowchart

```mermaid
flowchart TB
    subgraph Input["Input Sources"]
        SJ[("sources.json<br/>97 municipalities")]
        SU[("seen_urls<br/>Google Sheet")]
    end

    subgraph Phase1["Phase 1: Discovery"]
        GS[Get Sources]
        GU[Get Existing URLs]
        DNU[Discover New URLs]

        subgraph TypeStrategy["Type-Specific Strategy"]
            DP["Dedicated Portal<br/>map_url + keywords"]
            KI["Kortinfo<br/>scrape_url (JS SPA)"]
            NF["News Feed<br/>map_url + AI filter"]
            MS["Municipality Subsection<br/>map_url + keywords"]
            MIN["Minimal<br/>base URL only"]
        end
    end

    subgraph Phase2["Phase 2: AI Analysis"]
        SWR[Scrape with Retry]
        CR[Classify Relevance<br/>GPT-4o-mini]
        EPD[Extract Property Data<br/>GPT-4o]

        CR -->|"Not Relevant"| SKIP[Skip & Mark Seen]
        CR -->|"Relevant"| EPD
    end

    subgraph Phase3["Phase 3: Output"]
        PROP[("proposals<br/>Google Sheet")]
        DISC[("discoveries<br/>Google Sheet")]
        FAIL[("failures<br/>Google Sheet")]
        EVT[("events<br/>Google Sheet")]
        SLACK["Slack Notification"]
    end

    subgraph External["External APIs"]
        FC["Firecrawl API<br/>Web Scraping"]
        OAI["OpenAI API<br/>Classification & Extraction"]
    end

    SJ --> GS
    SU --> GU
    GS --> DNU
    GU --> DNU

    DNU --> TypeStrategy
    TypeStrategy --> FC
    FC --> DISC

    DNU -->|"New URLs Found"| SWR
    DNU -->|"No New URLs"| EVT

    SWR --> FC
    SWR -->|"Success"| CR
    SWR -->|"Failure"| FAIL

    CR --> OAI
    EPD --> OAI
    EPD -->|"Success"| PROP
    EPD -->|"Failure"| FAIL

    PROP --> SLACK
    FAIL --> SLACK
    EVT --> SLACK

    style Phase1 fill:#e1f5fe
    style Phase2 fill:#fff3e0
    style Phase3 fill:#e8f5e9
    style External fill:#fce4ec
```

## Description

This flowchart shows the complete system architecture of the Kommunal Grundsalg Monitor:

### Input Sources
- **sources.json** - 97 municipality URLs with type classification
- **seen_urls** - Previously processed URLs for deduplication

### Phase 1: Discovery
- Loads sources and existing URLs
- Uses type-specific strategies for each website type:
  - Dedicated portals: `map_url` with property keywords
  - Kortinfo sites: `scrape_url` (JavaScript SPA workaround)
  - News feeds: `map_url` + AI classification filter
  - Municipality subsections: `map_url` with keywords
  - Minimal sites: Base URL only

### Phase 2: AI Analysis
- **Scrape with Retry** - Fetches page content with retry logic
- **Classify Relevance** - GPT-4o-mini determines if content is property-related
- **Extract Property Data** - GPT-4o extracts structured data from relevant pages

### Phase 3: Output
- **discoveries** - Raw Firecrawl findings (audit trail)
- **proposals** - AI-analyzed property listings
- **failures** - Error tracking
- **events** - System logs and heartbeat
- **Slack** - Notifications for proposals and failures

### External APIs
- **Firecrawl** - Web scraping and content extraction
- **OpenAI** - AI classification and data extraction
