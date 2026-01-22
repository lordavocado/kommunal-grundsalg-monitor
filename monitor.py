import os
import json
from datetime import datetime, timezone
from typing import List, Optional
from firecrawl import FirecrawlApp
from openai import OpenAI
from sheets import append_row, get_rows

# Config
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FIRE_CRAWL_MAP_LIMIT = 50

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

def get_sources() -> List[str]:
    """Fetch municipal target URLs from the 'sources' sheet."""
    try:
        rows = get_rows("sources")
        if not rows:
            return []
        # Assume first column is the URL
        return [row[0] for row in rows if row and row[0].startswith("http")]
    except Exception as e:
        print(f"Error loading sources: {e}")
        return []

def discover_new_urls(base_url: str, seen_urls: set) -> List[str]:
    """Use Firecrawl to find new potential property listing URLs."""
    if not firecrawl:
        print("Firecrawl not initialized, skipping discovery.")
        return []

    print(f"Mapping {base_url}...")
    try:
        # Search for keywords in URLs to narrow down to property sales
        search_query = "grundsalg parcelhusgrunde erhvervsudstykning ejendomme til salg"
        map_result = firecrawl.map(base_url, params={
            "search": search_query,
            "limit": FIRE_CRAWL_MAP_LIMIT
        })
        
        discovered = map_result.get("links", [])
        new_urls = [url for url in discovered if url not in seen_urls]
        print(f"Found {len(new_urls)} new URLs out of {len(discovered)} mapped.")
        return new_urls
    except Exception as e:
        print(f"Firecrawl map failed for {base_url}: {e}")
        return []

def extract_property_data(url: str) -> Optional[dict]:
    """Scrape and use AI to extract structured data from a listing URL."""
    if not firecrawl or not openai_client:
        return None

    print(f"Scraping and extracting from {url}...")
    try:
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
        
        for url in potential_urls:
            data = extract_property_data(url)
            if data:
                # Append to events/results
                row = [
                    datetime.now(timezone.utc).isoformat(),
                    data.get("municipality"),
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
