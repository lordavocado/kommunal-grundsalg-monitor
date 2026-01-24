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

def is_property_related(url: str, content: str) -> bool:
    """Use AI to classify if content is about property sales (for news feed sites)."""
    # Quick keyword check first - if obvious property content, skip AI call
    property_keywords = [
        "grundsalg", "byggegrunde", "parcelhusgrunde", "erhvervsgrunde",
        "grunde til salg", "ejendomme til salg", "storparceller",
        "udstykning", "villagrunde", "boliggrunde"
    ]
    content_lower = content.lower()
    if any(kw in content_lower for kw in property_keywords):
        return True

    # Use AI for ambiguous cases
    if not openai_client:
        return False

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for classification
            messages=[
                {"role": "system", "content": "You classify Danish municipal web pages. Answer only 'yes' or 'no'."},
                {"role": "user", "content": f"Is this page about municipal property/land sales (grundsalg, byggegrunde, ejendomme til salg)? Content: {content[:2000]}"}
            ],
            max_tokens=10
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer == "yes" or answer == "ja"
    except Exception as e:
        print(f"Classification failed: {e}")
        return False

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

def extract_property_data(url: str) -> Optional[dict]:
    """Scrape and use AI to extract structured data from a listing URL."""
    if not firecrawl or not openai_client:
        return None

    print(f"Scraping and extracting from {url}...", flush=True)
    try:
        time.sleep(RATE_LIMIT_DELAY)  # Rate limit
        scrape_result = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
        content = scrape_result.get("markdown", "")
        
        if not content:
            return None

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a specialized assistant extracting Danish municipal property sale info (grundsalg). Output JSON only."},
                {"role": "user", "content": f"Extract the following fields from this markdown content: municipality, title, description, price, deadline, address. If a field is missing, use null. Language is Danish. Content: {content}"}
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
    print(f"Starting monitor run at {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load context
    sources = get_sources()
    seen_urls = get_existing_urls()
    
    if not sources:
        print("No sources found. Ensure 'sources' sheet exists and has URLs.")
        # Log a heartbeat even if no sources
        append_row("events", [datetime.now(timezone.utc).isoformat(), "system", "Run Summary", "No sources found"])
        return

    # 2. Process each source
    new_discoveries = []
    for source in sources:
        potential_urls = discover_new_urls(source, seen_urls)
        source_type = source.get("type", "municipality_subsection")
        config = DISCOVERY_CONFIG.get(source_type, {})

        for url in potential_urls:
            # For news feed sites, classify before full extraction
            if config.get("classify") and firecrawl:
                try:
                    time.sleep(RATE_LIMIT_DELAY)  # Rate limit
                    preview = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
                    content = preview.get("markdown", "")
                    if not is_property_related(url, content):
                        print(f"  Skipping non-property page: {url}", flush=True)
                        continue
                except Exception as e:
                    print(f"  Classification scrape failed: {e}", flush=True)

            data = extract_property_data(url)
            if data:
                # Append to events/results
                row = [
                    datetime.now(timezone.utc).isoformat(),
                    source["municipality"],
                    data.get("title"),
                    data.get("address"),
                    data.get("price"),
                    data.get("deadline"),
                    data.get("url"),
                    "new_listing"
                ]
                append_row("events", row)

                # Mark as seen
                append_row("seen_urls", [url, datetime.now(timezone.utc).isoformat()])
                seen_urls.add(url)
                new_discoveries.append(url)

    # 3. Final heartbeat/summary
    summary = f"Processed {len(sources)} sources. Found {len(new_discoveries)} new listings."
    append_row("events", [
        datetime.now(timezone.utc).isoformat(),
        "system",
        "Run Summary",
        summary
    ])
    print(f"✅ {summary}")

if __name__ == "__main__":
    main()
