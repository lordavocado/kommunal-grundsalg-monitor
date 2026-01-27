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
RETRY_DELAY = 5  # seconds to wait before retrying a failed request
MAX_RETRIES = 1  # number of retries for transient failures

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


def scrape_with_retry(url: str, params: dict = None) -> tuple[Optional[dict], Optional[str]]:
    """
    Scrape URL with retry logic for transient failures.
    Returns: (result_dict, error_message) - one will be None
    """
    if not firecrawl:
        return None, "Firecrawl not initialized"

    params = params or {"formats": ["markdown"]}
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            result = firecrawl.scrape_url(url, params=params)
            return result, None
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} for {url}...")
                time.sleep(RETRY_DELAY)

    return None, last_error


def log_failure(timestamp: str, url: str, source_id: str, failure_type: str, error_message: str):
    """Log a failure to the failures tab in Google Sheets."""
    try:
        append_row("failures", [timestamp, url, source_id, failure_type, error_message])
    except Exception as e:
        print(f"  Warning: Could not log failure to sheets: {e}")


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


def send_slack_notification(message: str, proposals: list = None, stats: dict = None):
    """Send notification to Slack when new proposals are found or failures occur."""
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

    details_lines = []

    # Add proposals section if any
    if proposals:
        for p in proposals[:10]:  # Limit to 10 in message
            conf = p.get('confidence', 0)
            conf_str = f"{int(conf * 100)}%" if isinstance(conf, (int, float)) else str(conf)
            details_lines.append(
                f"• {p.get('municipality', 'Unknown')}: {p.get('title', 'Untitled')} ({conf_str} confidence)\n  {p.get('url', '')}"
            )

    # Add failures section if any
    if stats:
        total_failures = len(stats.get("scrape_failed", [])) + len(stats.get("extraction_failed", []))
        if total_failures > 0:
            details_lines.append(f"\n❌ Failures ({total_failures}):")
            for fail in stats.get("scrape_failed", [])[:5]:
                details_lines.append(f"  • Scrape: {fail['url'][:60]}...")
            for fail in stats.get("extraction_failed", [])[:5]:
                details_lines.append(f"  • Extract: {fail['url'][:60]}...")
            if total_failures > 10:
                details_lines.append(f"  ... and {total_failures - 10} more")

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

    # Initialize stats for reliability tracking
    stats = {
        "sources_processed": 0,
        "urls_discovered": 0,
        "urls_attempted": 0,
        "scrape_success": 0,
        "scrape_failed": [],       # List of {"url": ..., "source_id": ..., "error": ...}
        "classification_success": 0,
        "classification_failed": [],
        "extraction_success": 0,
        "extraction_failed": [],
        "proposals_created": 0,
        "skipped_irrelevant": 0,
    }

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
        stats["sources_processed"] += 1
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
            stats["urls_discovered"] += 1

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

    proposals_list = []  # Collect for Slack notification

    for source, url in all_discoveries:
        stats["urls_attempted"] += 1
        source_id = source.get("municipality", "unknown")

        # Scrape content with retry logic
        scrape_result, scrape_error = scrape_with_retry(url, {"formats": ["markdown"]})

        if scrape_error:
            print(f"  ❌ Scrape FAILED for {url}: {scrape_error}", flush=True)
            stats["scrape_failed"].append({"url": url, "source_id": source_id, "error": scrape_error})
            log_failure(timestamp, url, source_id, "scrape_failed", scrape_error)
            # Still mark as seen to avoid re-processing
            append_row("seen_urls", [url, timestamp])
            seen_urls.add(url)
            continue

        stats["scrape_success"] += 1
        content = scrape_result.get("markdown", "") if scrape_result else ""

        # Classify relevance (loose filter)
        try:
            classification = classify_relevance(url, content)
            stats["classification_success"] += 1
        except Exception as e:
            print(f"  ❌ Classification FAILED for {url}: {e}", flush=True)
            stats["classification_failed"].append({"url": url, "source_id": source_id, "error": str(e)})
            log_failure(timestamp, url, source_id, "classification_failed", str(e))
            # Still mark as seen
            append_row("seen_urls", [url, timestamp])
            seen_urls.add(url)
            continue

        if not classification.get("is_relevant", False):
            print(f"  ⏭️ Skipping (not relevant): {url} - {classification.get('reason', '')}", flush=True)
            stats["skipped_irrelevant"] += 1
            # Mark as seen to avoid re-processing
            append_row("seen_urls", [url, timestamp])
            seen_urls.add(url)
            continue

        print(f"  ✓ Relevant ({classification.get('category', 'unknown')}): {url}", flush=True)

        # Extract structured data (reuse scraped content)
        try:
            data = extract_property_data(url, pre_scraped_content=content)
        except Exception as e:
            print(f"  ❌ Extraction FAILED for {url}: {e}", flush=True)
            stats["extraction_failed"].append({"url": url, "source_id": source_id, "error": str(e)})
            log_failure(timestamp, url, source_id, "extraction_failed", str(e))
            append_row("seen_urls", [url, timestamp])
            seen_urls.add(url)
            continue

        if data:
            stats["extraction_success"] += 1
            stats["proposals_created"] += 1

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

            # Collect for Slack notification
            proposals_list.append({
                "municipality": source.get("name", source.get("municipality", "")),
                "title": data.get("title", "Untitled"),
                "url": url,
                "confidence": data.get("confidence", 0)
            })
        else:
            # Extraction returned None (failed internally)
            stats["extraction_failed"].append({"url": url, "source_id": source_id, "error": "Extraction returned None"})
            log_failure(timestamp, url, source_id, "extraction_failed", "Extraction returned None")

        # Mark as seen
        append_row("seen_urls", [url, timestamp])
        seen_urls.add(url)

    # ============================================
    # PHASE 3: Summary + Slack Notification
    # ============================================
    total_failures = len(stats["scrape_failed"]) + len(stats["classification_failed"]) + len(stats["extraction_failed"])

    # Build detailed summary
    summary_parts = [
        f"Processed {stats['sources_processed']} sources",
        f"Discovered {stats['urls_discovered']} URLs",
        f"Scraped {stats['scrape_success']}/{stats['urls_attempted']} ({len(stats['scrape_failed'])} failed)",
        f"Proposals: {stats['proposals_created']}",
        f"Skipped: {stats['skipped_irrelevant']} (not relevant)",
    ]
    if total_failures > 0:
        summary_parts.append(f"⚠️ Total failures: {total_failures}")

    summary = " | ".join(summary_parts)
    append_row("events", [timestamp, "system", "Run Summary", summary, "", "", "", ""])
    print(f"\n✅ {summary}")

    # Print failure breakdown if any
    if total_failures > 0:
        print(f"\n⚠️ Failure breakdown:")
        print(f"   Scrape failures: {len(stats['scrape_failed'])}")
        print(f"   Classification failures: {len(stats['classification_failed'])}")
        print(f"   Extraction failures: {len(stats['extraction_failed'])}")

    # Send Slack notification if we found proposals OR had failures
    if stats["proposals_created"] > 0 or total_failures > 0:
        if total_failures > 0:
            message = f"🏠 Grundsalg Monitor: {stats['proposals_created']} proposals, ❌ {total_failures} failures"
        else:
            message = f"🏠 Grundsalg Monitor: Found {stats['proposals_created']} new property listings today!"

        send_slack_notification(message, proposals_list, stats)

if __name__ == "__main__":
    main()
