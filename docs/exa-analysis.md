# Exa.ai - Comprehensive Analysis

## Overview

| Attribute | Details |
|-----------|---------|
| **Name** | Exa.ai |
| **Type** | AI-powered search engine API |
| **Business Model** | SaaS / Pay-as-you-go |
| **Primary Use Case** | Web search and content retrieval for AI agents |
| **Notable Users** | Cursor, Perplexity, and other AI companies |
| **Differentiator** | Purpose-built for AI with own search index |

## What is Exa.ai?

Exa is a modern AI search engine providing web search capabilities through APIs and developer tools. Unlike traditional web scrapers, Exa maintains its own search index and is optimized for AI/LLM consumption.

**Key differentiator**: Exa is a **search engine**, not a web scraper. It finds relevant content across the web rather than crawling specific URLs. Think of it as "Google API for AI agents."

---

## Core Products / API Endpoints

### 1. Search API
Find web pages matching your query with AI-powered ranking.

```python
from exa_py import Exa

exa = Exa(api_key="your-api-key")
results = exa.search(
    query="Danish municipality property sales grundsalg",
    num_results=10,
    type="auto"  # auto, neural, or keyword
)
```

**Search Types**:
| Type | Description | Best For |
|------|-------------|----------|
| `auto` | Automatically selects best approach | General use |
| `neural` | Semantic/meaning-based search | Complex queries |
| `keyword` | Traditional keyword matching | Exact matches |
| `deep` | More thorough search | Research tasks |

### 2. Crawl API
Extract all pages from a specific website.

```python
results = exa.crawl(
    url="https://grundsalg.aarhus.dk",
    max_pages=100
)
```

### 3. Answer API
Get natural language answers with citations.

```python
answer = exa.answer(
    query="What properties are for sale in Aarhus?",
    text=True
)
```

### 4. Research API
Perform in-depth research with structured output.

```python
research = exa.research(
    query="Danish municipality property sales market",
    depth="comprehensive"
)
```

### 5. Websets API
Advanced search for complex queries returning thousands of results.

```python
webset = exa.websets.create(
    query="All Danish municipalities with property sales pages",
    max_results=1000
)
```

---

## Content Retrieval Options

When retrieving search results, you can request:

| Option | Description | Cost |
|--------|-------------|------|
| `text` | Full page text content | $1/1k pages |
| `highlights` | Key excerpts/snippets | $1/1k pages |
| `summary` | AI-generated summary | $1/1k pages |

```python
results = exa.search(
    query="grundsalg aarhus",
    num_results=10,
    contents={
        "text": True,
        "highlights": True,
        "summary": True
    }
)
```

---

## Pricing

### Pay-As-You-Go (Free to Start)
- **Free credits**: $10 to get started
- **No credit card required** for trial

### Search Pricing (per 1,000 requests)

| Search Type | Cost |
|-------------|------|
| Fast/Auto/Neural | $5 |
| Deep | $15 |

| Results per Search | Cost |
|-------------------|------|
| 1-25 results | $5/1k requests |
| 26-100 results | $25/1k requests |

### Content Extraction (per 1,000 pages)

| Content Type | Cost |
|--------------|------|
| Text | $1 |
| Highlights | $1 |
| Summary | $1 |

### Answer API (per 1,000 answers)
- Direct answers with citations: **$5**

### Research API (per 1,000 tasks)

| Tier | Cost per Operation | Cost per Page Read |
|------|-------------------|-------------------|
| exa-research | $5 | $5 |
| exa-research-pro | $5 | $10 |
| Reasoning tokens | $5/1M tokens | - |

### Enterprise Plan
- Up to 1,000 results per search
- Custom rate limits (QPS)
- Tailored content moderation
- 1:1 onboarding and support
- SLAs and MSAs
- Zero data retention option
- Volume discounts

---

## Cost Estimation for Our Use Case

### Scenario: Daily Municipality Monitoring (97 sources)

**Option A: Search-based discovery**
- 97 searches/day × $5/1k = ~$0.49/day
- Content for 200 pages × $1/1k = ~$0.20/day
- **Daily cost: ~$0.69**
- **Monthly cost: ~$21**

**Option B: Crawl-based discovery**
- 97 crawls/day (cost unclear, likely similar to search)
- Would need to test actual credit usage

**Comparison to Firecrawl**: Potentially cheaper ($21 vs $83/month), but:
- Exa is search-focused, not crawl-focused
- May not find all pages on a specific site
- Better for discovering content across the web

---

## Filtering & Customization

### Domain Filtering
```python
results = exa.search(
    query="grundsalg",
    include_domains=["aarhus.dk", "koege.dk"],
    exclude_domains=["facebook.com"]
)
```

### Date Filtering
```python
results = exa.search(
    query="grundsalg",
    start_published_date="2024-01-01",
    end_published_date="2024-12-31"
)
```

### Category Filtering
```python
results = exa.search(
    query="property sales",
    category="government"  # Filter by semantic category
)
```

---

## Accuracy Benchmarks (from Exa)

| Search Vertical | Exa Accuracy | vs. Competitors |
|-----------------|--------------|-----------------|
| Company Search | 62% | Beats Parallel, Brave |
| People Search | 63% | Beats competitors |
| Code Search | 73% | Highest accuracy |

---

## Advantages

1. **AI-Optimized**: Built specifically for LLM/AI agent use
2. **Own Index**: Not dependent on Google/Bing APIs
3. **Semantic Search**: Neural search understands meaning
4. **Flexible Pricing**: Pay only for what you use
5. **Multiple Endpoints**: Search, crawl, answer, research
6. **Content Options**: Text, highlights, summaries
7. **No Infrastructure**: Fully managed service
8. **Fast**: Optimized for real-time AI workflows
9. **SOC 2 Compliant**: Enterprise security

## Limitations

1. **Search vs. Crawl**: Not designed for exhaustive site crawling
2. **Index Coverage**: May not index all pages (especially dynamic content)
3. **Danish Content**: Unclear how well it indexes Danish municipality sites
4. **Cost at Scale**: Can add up with high volume
5. **API Dependency**: Requires internet, subject to rate limits
6. **No JavaScript Rendering**: Relies on indexed content

---

## Use Cases

### Best For
- AI agent research capabilities
- Semantic web search
- Content discovery across multiple sites
- News and article aggregation
- Competitive intelligence
- Lead generation (finding companies, people)
- RAG system data sourcing

### Not Ideal For
- Exhaustive crawling of specific websites
- Real-time monitoring of page changes
- JavaScript-heavy single-page applications
- Sites not in Exa's index
- High-frequency, low-latency scraping

---

## Comparison to Firecrawl

| Aspect | Exa.ai | Firecrawl |
|--------|--------|-----------|
| **Type** | Search engine | Web scraper |
| **Approach** | Find content across web | Crawl specific URLs |
| **JavaScript** | No (indexed content) | Yes (full rendering) |
| **map_url equivalent** | Search API | Native map_url |
| **Best for** | Discovery | Extraction |
| **Cost (monthly)** | ~$21 (estimated) | ~$83 |
| **Index** | Own index | On-demand crawl |

---

## Suitability for Grundsalg Monitor

### Potential Benefits
- Could discover new municipality pages we don't know about
- Semantic search for "grundsalg" across Danish web
- Lower cost than Firecrawl

### Potential Issues
- May not index all Danish municipality subpages
- Not designed for monitoring specific URL changes
- Would need to test coverage of our 97 sources
- Different paradigm (search vs. crawl)

### Recommendation
**Exa is complementary, not a replacement** for Firecrawl in our use case:
- Firecrawl: Monitor known URLs, extract from specific pages
- Exa: Discover new sources, find mentions across the web

---

## Quick Start

### Installation
```bash
pip install exa-py
```

### Basic Usage
```python
from exa_py import Exa

exa = Exa(api_key="your-api-key")

# Search
results = exa.search("Danish property sales grundsalg", num_results=10)

# Get content
results_with_content = exa.search(
    "grundsalg aarhus",
    num_results=10,
    contents={"text": True, "summary": True}
)

# Crawl a site
site_pages = exa.crawl("https://grundsalg.aarhus.dk", max_pages=50)
```

---

## Resources

- **Website**: https://exa.ai
- **Documentation**: https://exa.ai/docs
- **Pricing**: https://exa.ai/pricing
- **Python SDK**: `pip install exa-py`
- **JavaScript SDK**: `npm install exa-js`

---

*Last updated: January 2026*
