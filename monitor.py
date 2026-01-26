import os
import json
import time
from datetime import datetime, timezone
from typing import List, Optional
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from openai import OpenAI
from sheets import append_row, get_rows

# Rate limiting: Firecrawl free tier = 15 req/min, so ~4 seconds between requests
RATE_LIMIT_DELAY = 4.5  # seconds between Firecrawl API calls

# Load environment variables from env.local
load_dotenv('env.local')

# Config
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Type-specific discovery configuration
DISCOVERY_CONFIG = {
    "dedicated_portal": {
        "limit": 100,
        "keywords": "villagrunde storparceller erhvervsgrunde parcelhusgrunde",
        "classify": False
    },
    "kortinfo": {
        "limit": 100,
        "keywords": "parcelhusgrunde boliggrunde erhvervsgrunde grund plot area",
        "classify": False
    },
    "news_feed": {
        "limit": 20,
        "keywords": "grundsalg byggegrunde ejendomme udbud salg",
        "classify": True  # Use AI to filter irrelevant news
    },
    "municipality_subsection": {
        "limit": 50,
        "keywords": "grundsalg parcelhusgrunde erhvervsgrunde byggegrunde",
        "classify": False
    },
    "minimal": {
        "limit": 5,
        "keywords": "grundsalg ejendomme",
        "classify": False
    }
}

# Init clients
firecrawl = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_existing_urls() -> set:
    """Fetch already processed URLs from the 'seen_urls' sheet."""
    try:
        rows = get_rows("seen_urls")
        if not rows:
            return set()
        # Assume first column is the URL
        return {row[0] for row in rows if row}
    except Exception as e:
        print(f"Warning: Could not load seen_urls: {e}")
        return set()

def get_sources_from_json() -> List[dict]:
    """Load sources from local sources.json file with type classification."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "sources.json")
        with open(json_path) as f:
            data = json.load(f)
        sources = []
        for s in data.get("sources", []):
            if s.get("url", "").startswith("http"):
                sources.append({
                    "municipality": s.get("id", ""),
                    "name": s.get("name", ""),
                    "url": s.get("url", ""),
                    "type": s.get("type", "municipality_subsection"),
                    "region": s.get("region", "")
                })
        return sources
    except Exception as e:
        print(f"Error loading sources.json: {e}")
        return []

def get_sources() -> List[dict]:
    """Fetch municipal target URLs - prefer local JSON, fallback to sheets."""
    sources = get_sources_from_json()
    if sources:
        print(f"Loaded {len(sources)} sources from sources.json")
        return sources

    # Fallback to Google Sheets
    try:
        rows = get_rows("sources")
        if not rows or len(rows) < 2:
            return []
        sources = []
        for row in rows[1:]:
            if len(row) >= 3 and row[2] and row[2].startswith("http"):
                sources.append({
                    "municipality": row[0],
                    "name": row[1],
                    "url": row[2],
                    "type": "municipality_subsection"  # Default type
                })
        print(f"Loaded {len(sources)} sources from Google Sheets (fallback)")
        return sources
    except Exception as e:
        print(f"Error loading sources: {e}")
        return []

def classify_relevance(url: str, content: str) -> dict:
    """
    Classify if content is property-related using keywords + AI (loose filter).
    Returns structured response with is_relevant, confidence, category, reason.
    """
    result = {
        "is_relevant": False,
        "confidence": 0.0,
        "category": "unknown",
        "reason": ""
    }

    # Quick keyword check first - if obvious property content, high confidence
    property_keywords = [
        "grundsalg", "byggegrunde", "parcelhusgrunde", "erhvervsgrunde",
        "grunde til salg", "ejendomme til salg", "storparceller",
        "udstykning", "villagrunde", "boliggrunde", "udbud", "til salg",
        "erhvervsgrund", "parcelhusgrund", "boliggrund"
    ]
    content_lower = content.lower()
    matched_keywords = [kw for kw in property_keywords if kw in content_lower]

    if matched_keywords:
        result["is_relevant"] = True
        result["confidence"] = min(0.5 + len(matched_keywords) * 0.1, 0.95)
        result["category"] = "keyword_match"
        result["reason"] = f"Matched keywords: {', '.join(matched_keywords[:3])}"
        return result

    # Filter out obvious non-property pages
    skip_patterns = [
        "kontakt", "cookie", "privatlivspolitik", "sitemap.xml",
        "om kommunen", "borgerservice", "job i kommunen"
    ]
    if any(pattern in content_lower[:500] for pattern in skip_patterns):
        result["reason"] = "Appears to be contact/policy page"
        return result

    # Use AI for ambiguous cases (loose filter - include anything potentially related)
    if not openai_client:
        # Without AI, be permissive
        result["is_relevant"] = True
        result["confidence"] = 0.3
        result["reason"] = "No AI available, including by default"
        return result

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You classify Danish municipal web pages. Output JSON only:
{"is_relevant": true/false, "confidence": 0.0-1.0, "category": "land_sale"|"property_sale"|"tender"|"announcement"|"news"|"other", "reason": "brief explanation"}

Use LOOSE filtering - include anything potentially related to:
- Land/property for sale (grundsalg, byggegrunde, ejendomme)
- Upcoming sales or tenders
- Property development announcements
- Area development plans with potential sales

Only exclude clearly irrelevant pages (general news, contact info, policies)."""},
                {"role": "user", "content": f"Classify this page (URL: {url}):\n\n{content[:2000]}"}
            ],
            response_format={"type": "json_object"},
            max_tokens=150
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Classification failed: {e}")
        # On error, be permissive (loose filter)
        result["is_relevant"] = True
        result["confidence"] = 0.2
        result["reason"] = f"Classification error, including by default: {e}"
        return result


def is_property_related(url: str, content: str) -> bool:
    """Legacy wrapper for classify_relevance - returns bool for backward compatibility."""
    result = classify_relevance(url, content)
    return result.get("is_relevant", False)

def discover_kortinfo_urls(base_url: str, seen_urls: set) -> List[str]:
    """Extract property URLs from kortinfo sites via scrape (they're JavaScript SPAs)."""
    if not firecrawl:
        return []

    print(f"Scraping kortinfo site {base_url}...", flush=True)
    try:
        time.sleep(RATE_LIMIT_DELAY)  # Rate limit
        result = firecrawl.scrape_url(base_url, params={
            "formats": ["markdown", "links"]
        })

        # Get links from the scrape result
        links = result.get("links", [])

        # Filter to property-related URLs
        property_patterns = [
            "/grund/", "/plot/", "/area/", "/Boliggrunde/", "/Erhvervsgrunde/",
            "/udstykning/", "/omraade/", "/Parcelhusgrunde/", "/Storparceller/"
        ]

        new_urls = [
            url for url in links
            if any(p.lower() in url.lower() for p in property_patterns)
            and url not in seen_urls
            and not url.lower().endswith('.pdf')
        ]

        # If no property URLs found via patterns, include all kortinfo subpages
        if not new_urls:
            base_domain = base_url.split('/')[2]
            new_urls = [
                url for url in links
                if base_domain in url
                and url != base_url
                and url not in seen_urls
                and not url.lower().endswith('.pdf')
            ]

        print(f"Found {len(new_urls)} property URLs from kortinfo scrape.")
        return new_urls
    except Exception as e:
        print(f"Kortinfo scrape failed for {base_url}: {e}")
        return []

def discover_new_urls(source: dict, seen_urls: set) -> List[str]:
    """Use Firecrawl to find new potential property listing URLs with type-specific config."""
    if not firecrawl:
        print("Firecrawl not initialized, skipping discovery.")
        return []

    base_url = source.get("url", "")
    source_type = source.get("type", "municipality_subsection")
    config = DISCOVERY_CONFIG.get(source_type, DISCOVERY_CONFIG["municipality_subsection"])

    # KORTINFO: Use scrape instead of map (JavaScript SPA)
    if source_type == "kortinfo":
        return discover_kortinfo_urls(base_url, seen_urls)

    # MINIMAL: Just return the base URL for direct scraping
    if source_type == "minimal":
        print(f"Minimal site {base_url} - returning base URL only")
        return [base_url] if base_url not in seen_urls else []

    # OTHER TYPES: Use map_url
    print(f"Mapping {base_url} (type: {source_type}, limit: {config['limit']})...", flush=True)
    try:
        time.sleep(RATE_LIMIT_DELAY)  # Rate limit
        map_result = firecrawl.map_url(base_url, params={
            "search": config["keywords"],
            "limit": config["limit"]
        })

        # map_url returns a list directly
        discovered = map_result if isinstance(map_result, list) else map_result.get("links", [])

        # Filter out PDFs and already seen URLs
        new_urls = [
            url for url in discovered
            if url not in seen_urls and not url.lower().endswith('.pdf')
        ]

        print(f"Found {len(new_urls)} new URLs out of {len(discovered)} mapped.")
        return new_urls
    except Exception as e:
        print(f"Firecrawl map failed for {base_url}: {e}")
        return []

EXTRACTION_PROMPT = """Analyze this Danish municipality page. Output JSON:
{
  "is_property_listing": boolean,  // Is this about property/land for sale or development?
  "confidence": 0.0-1.0,           // How confident are you?
  "title": string,                 // Brief title
  "municipality": string,          // Which kommune?
  "summary": string                // 1-2 sentence description in Danish
}

Set is_property_listing=true if this is about: grundsalg, byggegrunde, parcelhusgrunde, erhvervsgrunde, ejendomme til salg, or any property/land sale announcement.
Language is Danish. Output JSON only."""


def send_slack_notification(message: str, proposals: list = None):
    """Send notification to Slack when new proposals are found."""
    import requests

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set, skipping Slack notification")
        return

    # For Slack Workflow Builder, we send structured data
    payload = {
        "message": message,
        "proposals_count": len(proposals) if proposals else 0,
        "details": ""
    }

    if proposals:
        # Format proposals as bullet list
        details_lines = []
        for p in proposals[:10]:  # Limit to 10 in message
            conf = p.get('confidence', 0)
            conf_str = f"{int(conf * 100)}%" if isinstance(conf, (int, float)) else str(conf)
            details_lines.append(
                f"* {p.get('municipality', 'Unknown')}: {p.get('title', 'Untitled')} ({conf_str} confidence)\n  {p.get('url', '')}"
            )
        payload["details"] = "\n".join(details_lines)

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Slack notification sent successfully")
    except Exception as e:
        print(f"Slack notification failed: {e}")


def extract_property_data(url: str, pre_scraped_content: str = None) -> Optional[dict]:
    """Scrape and use AI to extract structured data from a listing URL."""
    if not openai_client:
        return None

    # Use pre-scraped content if available (avoids double scraping)
    content = pre_scraped_content
    if not content and firecrawl:
        print(f"Scraping and extracting from {url}...", flush=True)
        try:
            time.sleep(RATE_LIMIT_DELAY)  # Rate limit
            scrape_result = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
            content = scrape_result.get("markdown", "")
        except Exception as e:
            print(f"Scrape failed for {url}: {e}")
            return None

    if not content:
        return None

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract property data from this page (URL: {url}):\n\n{content[:8000]}"}
            ],
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content)
        data["url"] = url
        return data
    except Exception as e:
        print(f"Extraction failed for {url}: {e}")
        return None

def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"Starting monitor run at {timestamp}")

    # 1. Load context
    sources = get_sources()
    seen_urls = get_existing_urls()

    if not sources:
        print("No sources found. Ensure 'sources' sheet exists and has URLs.")
        append_row("events", [timestamp, "system", "Run Summary", "No sources found", "", "", "", ""])
        return

    # ============================================
    # PHASE 1: Discovery - Find all new URLs
    # ============================================
    print(f"\n📡 Phase 1: Discovering new URLs from {len(sources)} sources...\n")
    all_discoveries = []  # List of (source, url) tuples

    for source in sources:
        new_urls = discover_new_urls(source, seen_urls)

        # Log each discovery to 'discoveries' tab (raw Firecrawl findings)
        for url in new_urls:
            append_row("discoveries", [
                timestamp,
                source.get("municipality", ""),
                source.get("name", ""),
                url,
                source.get("type", "")
            ])
            all_discoveries.append((source, url))

    discovery_count = len(all_discoveries)
    print(f"\n📊 Discovery complete: Found {discovery_count} new URLs")

    # ============================================
    # PHASE 2: AI Analysis (only if new URLs found)
    # ============================================
    if not all_discoveries:
        summary = f"Processed {len(sources)} sources. No new URLs found - AI analysis skipped."
        append_row("events", [timestamp, "system", "Run Summary", summary, "", "", "", ""])
        print(f"\n✅ {summary}")
        return

    print(f"\n🤖 Phase 2: Running AI analysis on {discovery_count} URLs...\n")

    proposals_count = 0
    skipped_count = 0
    proposals_list = []  # Collect for Slack notification

    for source, url in all_discoveries:
        # Scrape content once for both classification and extraction
        content = None
        if firecrawl:
            try:
                time.sleep(RATE_LIMIT_DELAY)
                scrape_result = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
                content = scrape_result.get("markdown", "")
            except Exception as e:
                print(f"  Scrape failed for {url}: {e}", flush=True)
                continue

        # Classify relevance (loose filter)
        classification = classify_relevance(url, content or "")

        if not classification.get("is_relevant", False):
            print(f"  ⏭️ Skipping (not relevant): {url} - {classification.get('reason', '')}", flush=True)
            skipped_count += 1
            # Still mark as seen to avoid re-processing
            append_row("seen_urls", [url, timestamp])
            seen_urls.add(url)
            continue

        print(f"  ✓ Relevant ({classification.get('category', 'unknown')}): {url}", flush=True)

        # Extract structured data (reuse scraped content)
        data = extract_property_data(url, pre_scraped_content=content)

        if data:
            # Simplified proposals row: timestamp, municipality, title, url, confidence, summary
            row = [
                timestamp,
                source.get("municipality", ""),
                data.get("title", ""),
                url,
                data.get("confidence", 0),
                data.get("summary", "")
            ]
            append_row("proposals", row)
            proposals_count += 1

            # Collect for Slack notification
            proposals_list.append({
                "municipality": source.get("name", source.get("municipality", "")),
                "title": data.get("title", "Untitled"),
                "url": url,
                "confidence": data.get("confidence", 0)
            })

        # Mark as seen
        append_row("seen_urls", [url, timestamp])
        seen_urls.add(url)

    # ============================================
    # PHASE 3: Summary + Slack Notification
    # ============================================
    summary = f"Processed {len(sources)} sources. Discovered {discovery_count} URLs → {proposals_count} proposals. Skipped: {skipped_count} (not relevant)."
    append_row("events", [timestamp, "system", "Run Summary", summary, "", "", "", ""])
    print(f"\n✅ {summary}")

    # Send Slack notification if we found proposals
    if proposals_count > 0:
        send_slack_notification(
            f"🏠 Grundsalg Monitor: Found {proposals_count} new property listings today!",
            proposals_list
        )

if __name__ == "__main__":
    main()
