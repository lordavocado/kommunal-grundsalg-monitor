#!/usr/bin/env python3
"""
Test script to evaluate crawl4ai as a Firecrawl replacement.
Requires Python 3.10+ and crawl4ai installed.

Install:
    brew install python@3.11
    /opt/homebrew/bin/python3.11 -m pip install crawl4ai
    /opt/homebrew/bin/python3.11 -m crawl4ai.install

Run:
    /opt/homebrew/bin/python3.11 test_crawl4ai.py
"""

import asyncio
import time
from typing import List


async def test_basic_scrape():
    """Test 1: Basic scraping - does it return markdown like Firecrawl?"""
    from crawl4ai import AsyncWebCrawler

    print("=" * 60)
    print("TEST 1: Basic Scrape")
    print("=" * 60)

    url = "https://grundsalg.aarhus.dk/"
    print(f"URL: {url}")

    start = time.time()
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    elapsed = time.time() - start

    markdown_len = len(result.markdown) if result.markdown else 0
    links_count = len(result.links) if hasattr(result, 'links') and result.links else 0

    print(f"Time: {elapsed:.2f}s")
    print(f"Markdown length: {markdown_len} chars")
    print(f"Links found: {links_count}")

    if markdown_len > 500:
        print("✅ PASS: Sufficient markdown content")
    else:
        print("❌ FAIL: Markdown too short")

    # Show sample of content
    if result.markdown:
        print(f"\nSample content (first 300 chars):")
        print("-" * 40)
        print(result.markdown[:300])

    return markdown_len > 500


async def test_kortinfo_javascript():
    """Test 2: JavaScript SPA handling - can it render Kortinfo sites?"""
    from crawl4ai import AsyncWebCrawler

    print("\n" + "=" * 60)
    print("TEST 2: Kortinfo JavaScript SPA")
    print("=" * 60)

    url = "https://grundsalg.kortinfo.net/odense-grundsalg/"
    print(f"URL: {url}")

    start = time.time()
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    elapsed = time.time() - start

    markdown_len = len(result.markdown) if result.markdown else 0
    links_count = len(result.links) if hasattr(result, 'links') and result.links else 0

    print(f"Time: {elapsed:.2f}s")
    print(f"Markdown length: {markdown_len} chars")
    print(f"Links extracted: {links_count}")

    passed = markdown_len > 200 and links_count > 0
    if passed:
        print("✅ PASS: Content rendered and links extracted")
    else:
        print("❌ FAIL: JS rendering may not have worked")

    # Show some extracted links
    if hasattr(result, 'links') and result.links:
        print(f"\nSample links (first 5):")
        for link in result.links[:5]:
            print(f"  - {link}")

    return passed


async def test_link_extraction():
    """Test 3: Link extraction - does it extract links properly?"""
    from crawl4ai import AsyncWebCrawler

    print("\n" + "=" * 60)
    print("TEST 3: Link Extraction")
    print("=" * 60)

    url = "https://grundsalg.aarhus.dk/"
    print(f"URL: {url}")

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    links = result.links if hasattr(result, 'links') and result.links else []
    internal_links = [l for l in links if 'aarhus' in l.lower()]
    property_links = [l for l in links if any(kw in l.lower() for kw in ['grund', 'parcel', 'erhverv', 'bolig'])]

    print(f"Total links: {len(links)}")
    print(f"Internal links: {len(internal_links)}")
    print(f"Property-related links: {len(property_links)}")

    passed = len(links) >= 5
    if passed:
        print("✅ PASS: Sufficient links extracted")
    else:
        print("❌ FAIL: Too few links")

    if property_links:
        print(f"\nProperty-related links found:")
        for link in property_links[:10]:
            print(f"  - {link}")

    return passed


async def test_deep_crawl():
    """Test 4: Deep crawl - can it discover URLs like Firecrawl's map_url?"""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    print("\n" + "=" * 60)
    print("TEST 4: Deep Crawl Discovery")
    print("=" * 60)

    url = "https://grundsalg.aarhus.dk/"
    print(f"URL: {url}")
    print("Strategy: BFS, max_depth=1, max_pages=15")

    start = time.time()

    # Configure deep crawl
    browser_config = BrowserConfig(headless=True)

    discovered_urls: List[str] = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # First, get the initial page and its links
        result = await crawler.arun(url=url)

        # Collect links from the page
        if hasattr(result, 'links') and result.links:
            for link in result.links:
                if 'grundsalg.aarhus.dk' in link and link not in discovered_urls:
                    discovered_urls.append(link)
                    if len(discovered_urls) >= 15:
                        break

    elapsed = time.time() - start

    print(f"Time: {elapsed:.2f}s")
    print(f"URLs discovered: {len(discovered_urls)}")

    passed = len(discovered_urls) >= 5
    if passed:
        print("✅ PASS: Multiple URLs discovered")
    else:
        print("❌ FAIL: Not enough URLs found")

    print(f"\nDiscovered URLs:")
    for url in discovered_urls[:10]:
        print(f"  - {url}")

    return passed


async def test_keyword_filtering():
    """Test 5: Can we filter discovered URLs by property keywords?"""
    from crawl4ai import AsyncWebCrawler

    print("\n" + "=" * 60)
    print("TEST 5: Keyword Filtering")
    print("=" * 60)

    keywords = ["grundsalg", "parcelhusgrund", "erhvervsgrund", "boliggrund", "storparcel"]
    print(f"Keywords: {keywords}")

    url = "https://grundsalg.aarhus.dk/"

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    links = result.links if hasattr(result, 'links') and result.links else []

    # Filter links by keywords
    matched_links = []
    for link in links:
        link_lower = link.lower()
        if any(kw in link_lower for kw in keywords):
            matched_links.append(link)

    print(f"Total links: {len(links)}")
    print(f"Keyword-matched links: {len(matched_links)}")

    passed = len(matched_links) >= 3
    if passed:
        print("✅ PASS: Keyword filtering works")
    else:
        print("❌ FAIL: Not enough keyword matches")

    if matched_links:
        print(f"\nMatched URLs:")
        for link in matched_links[:10]:
            print(f"  - {link}")

    return passed


async def main():
    """Run all tests and summarize results."""
    print("\n" + "=" * 60)
    print("CRAWL4AI EVALUATION TEST SUITE")
    print("=" * 60)
    print("Testing crawl4ai as potential Firecrawl replacement\n")

    results = {}

    try:
        results['basic_scrape'] = await test_basic_scrape()
    except Exception as e:
        print(f"❌ Test 1 ERROR: {e}")
        results['basic_scrape'] = False

    try:
        results['kortinfo_js'] = await test_kortinfo_javascript()
    except Exception as e:
        print(f"❌ Test 2 ERROR: {e}")
        results['kortinfo_js'] = False

    try:
        results['link_extraction'] = await test_link_extraction()
    except Exception as e:
        print(f"❌ Test 3 ERROR: {e}")
        results['link_extraction'] = False

    try:
        results['deep_crawl'] = await test_deep_crawl()
    except Exception as e:
        print(f"❌ Test 4 ERROR: {e}")
        results['deep_crawl'] = False

    try:
        results['keyword_filter'] = await test_keyword_filtering()
    except Exception as e:
        print(f"❌ Test 5 ERROR: {e}")
        results['keyword_filter'] = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed >= 4:
        print("\n🎉 crawl4ai is VIABLE for migration!")
        print("   Recommendation: Proceed with full migration")
    elif passed >= 2:
        print("\n⚠️ crawl4ai shows PARTIAL viability")
        print("   Recommendation: Investigate failed tests before migrating")
    else:
        print("\n❌ crawl4ai may NOT be suitable")
        print("   Recommendation: Consider alternatives or wait for Firecrawl credits")


if __name__ == "__main__":
    asyncio.run(main())
