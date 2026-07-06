#!/usr/bin/env python3
"""
Q-Mol LinkedIn Prospect Extractor
=================================
Searches LinkedIn for prospects in the drug discovery / cheminformatics space
and extracts their profile data to CSV. Uses Kimi WebBridge to control Chrome.

SAFETY-FIRST DESIGN:
- Rate limiting with human-like delays
- No automated connection requests (extraction only)
- Respects LinkedIn's terms of service
- Session-based tracking to avoid duplicate searches

Usage:
    python linkedin_prospect_extractor.py --search "computational chemistry"
    python linkedin_prospect_extractor.py --search-all
    python linkedin_prospect_extractor.py --extract-profiles --input prospects_raw.csv
    python linkedin_prospect_extractor.py --score-prospects

Author: Q-Mol Automation Team
"""

import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urlencode

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "extractor_config.json"

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()
WEBBRIDGE_URL = CONFIG["webbridge_url"]
SESSION_NAME = CONFIG["session_name"]
OUTPUT_DIR = Path(CONFIG["output_dir"])
DATA_DIR = Path(CONFIG["data_dir"])
SAFETY = CONFIG["safety_limits"]
EXTRACTION = CONFIG["extraction"]

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Anti-Detection & Safety Utilities
# ---------------------------------------------------------------------------

class SafetyGuard:
    """Tracks daily limits and enforces rate limiting."""
    
    def __init__(self):
        self.state_file = DATA_DIR / "extractor_state.json"
        self.state = self._load_state()
        self.today = datetime.now().strftime("%Y-%m-%d")
        self._ensure_today()
    
    def _load_state(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"daily_counts": {}, "last_action_time": None, "searches_done": []}
    
    def _save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
    
    def _ensure_today(self):
        if self.today not in self.state["daily_counts"]:
            self.state["daily_counts"][self.today] = {
                "profile_views": 0,
                "searches": 0,
                "pages_scrolled": 0,
                "profiles_extracted": 0
            }
    
    def can_search(self) -> bool:
        return self.state["daily_counts"][self.today]["searches"] < SAFETY["max_searches_per_day"]
    
    def can_view_profile(self) -> bool:
        return self.state["daily_counts"][self.today]["profile_views"] < SAFETY["max_profile_views_per_day"]
    
    def can_extract_more(self, count: int = 1) -> bool:
        current = self.state["daily_counts"][self.today]["profiles_extracted"]
        return (current + count) <= SAFETY["max_profile_views_per_day"]
    
    def record_search(self):
        self.state["daily_counts"][self.today]["searches"] += 1
        self._save_state()
    
    def record_profile_view(self, count: int = 1):
        self.state["daily_counts"][self.today]["profile_views"] += count
        self._save_state()
    
    def record_extraction(self, count: int = 1):
        self.state["daily_counts"][self.today]["profiles_extracted"] += count
        self._save_state()
    
    def human_delay(self, min_sec: int = None, max_sec: int = None):
        """Wait for a random duration to simulate human behavior."""
        min_sec = min_sec or SAFETY["min_delay_between_actions_seconds"]
        max_sec = max_sec or SAFETY["max_delay_between_actions_seconds"]
        delay = random.uniform(min_sec, max_sec)
        print(f"  ⏱️  Waiting {delay:.1f}s...")
        time.sleep(delay)
    
    def profile_delay(self):
        """Longer delay between profile views."""
        delay = random.uniform(
            SAFETY["min_delay_between_profiles_seconds"],
            SAFETY["max_delay_between_profiles_seconds"]
        )
        print(f"  ⏱️  Profile delay: {delay:.1f}s...")
        time.sleep(delay)
    
    def get_status(self) -> dict:
        return {
            "date": self.today,
            "searches": self.state["daily_counts"][self.today]["searches"],
            "searches_limit": SAFETY["max_searches_per_day"],
            "profile_views": self.state["daily_counts"][self.today]["profile_views"],
            "profile_views_limit": SAFETY["max_profile_views_per_day"],
            "profiles_extracted": self.state["daily_counts"][self.today]["profiles_extracted"]
        }
    
    def print_status(self):
        s = self.get_status()
        print(f"\n{'='*50}")
        print("DAILY SAFETY STATUS")
        print(f"{'='*50}")
        print(f"Searches:        {s['searches']}/{s['searches_limit']}")
        print(f"Profile views:   {s['profile_views']}/{s['profile_views_limit']}")
        print(f"Extracted:       {s['profiles_extracted']}")
        print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# WebBridge Client
# ---------------------------------------------------------------------------

class WebBridgeClient:
    """Low-level client for Kimi WebBridge."""
    
    def __init__(self, session: str = SESSION_NAME):
        self.session = session
        self.url = WEBBRIDGE_URL
    
    def _send(self, action: str, args: dict) -> dict:
        payload = {"action": action, "args": args, "session": self.session}
        try:
            resp = requests.post(self.url, json=payload, timeout=30)
            return resp.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def navigate(self, url: str, new_tab: bool = False) -> dict:
        return self._send("navigate", {"url": url, "newTab": new_tab})
    
    def snapshot(self) -> dict:
        return self._send("snapshot", {})
    
    def click(self, selector: str) -> dict:
        return self._send("click", {"selector": selector})
    
    def fill(self, selector: str, value: str) -> dict:
        return self._send("fill", {"selector": selector, "value": value})
    
    def evaluate(self, code: str) -> dict:
        return self._send("evaluate", {"code": code})
    
    def screenshot(self, path: str = None) -> dict:
        args = {}
        if path:
            args["path"] = str(path)
        return self._send("screenshot", args)
    
    def scroll_down(self, pixels: int = 800) -> dict:
        code = f"window.scrollBy(0, {pixels});"
        return self.evaluate(code)
    
    def scroll_to_bottom(self) -> dict:
        code = "window.scrollTo(0, document.body.scrollHeight);"
        return self.evaluate(code)
    
    def get_page_info(self) -> dict:
        """Get current URL and title."""
        code = "JSON.stringify({url: window.location.href, title: document.title})"
        result = self.evaluate(code)
        if result.get("ok"):
            try:
                return json.loads(result.get("data", {}).get("value", "{}"))
            except:
                pass
        return {}


# ---------------------------------------------------------------------------
# LinkedIn Search URL Builder
# ---------------------------------------------------------------------------

class LinkedInSearchBuilder:
    """Builds LinkedIn search URLs for people search."""
    
    BASE_URL = "https://www.linkedin.com/search/results/people/"
    
    # Target keywords for Q-Mol
    KEYWORD_SETS = [
        # Primary: direct relevance
        ["cheminformatics", "drug discovery"],
        ["computational chemistry", "virtual screening"],
        ["molecular modeling", "medicinal chemistry"],
        ["ADMET", "QSAR", "pharmaceutical"],
        ["docking", "molecular dynamics"],
        ["compound library", "screening", "ML"],
        ["RDKit", "Python", "drug design"],
        ["AI drug discovery", "machine learning", "molecules"],
        ["CADD", "computer aided drug design"],
        ["hit identification", "lead optimization"],
        ["bioinformatics", "target identification"],
        ["pharmacophore", "SAR"],
        ["deep learning", "molecular property prediction"],
        ["generative chemistry", "de novo design"],
        ["high throughput screening", "HTS"],
    ]
    
    JOB_TITLES = [
        "Scientist", "Senior Scientist", "Principal Scientist",
        "Director", "Founder", "CTO", "CEO",
        "Head of Chemistry", "Cheminformatician",
        "Computational Chemist", "Medicinal Chemist",
        "Data Scientist", "ML Engineer",
        "Research Scientist", "Group Leader",
        "VP Research", "Chief Scientific Officer"
    ]
    
    @classmethod
    def build_url(cls, keywords: List[str], geo_urn: str = None, 
                  company_size: str = None, title: str = None,
                  page: int = 1) -> str:
        """Build a LinkedIn people search URL."""
        params = {
            "keywords": " ".join(keywords),
            "origin": "GLOBAL_SEARCH_HEADER",
            "sid": f"qm{random.randint(100,999)}"
        }
        
        if geo_urn:
            params["geoUrn"] = geo_urn
        
        if company_size:
            params["companySize"] = company_size
        
        # LinkedIn uses facet-based filtering
        facets = []
        if title:
            # title is part of keywords on regular search
            params["keywords"] = f"{title} {params['keywords']}"
        
        if page > 1:
            params["page"] = page
        
        return f"{cls.BASE_URL}?{urlencode(params)}"
    
    @classmethod
    def get_all_search_configs(cls) -> List[dict]:
        """Generate all search configurations."""
        configs = []
        geos = CONFIG["search_targets"]["geographies"]
        
        for keyword_set in cls.KEYWORD_SETS:
            for geo in geos:
                configs.append({
                    "keywords": keyword_set,
                    "geo_urn": geo["urn"],
                    "geo_name": geo["name"],
                    "label": f"{' '.join(keyword_set)} in {geo['name']}"
                })
        
        return configs


# ---------------------------------------------------------------------------
# Prospect Extractor Engine
# ---------------------------------------------------------------------------

class ProspectExtractor:
    """Extracts prospect data from LinkedIn search results."""
    
    def __init__(self):
        self.wb = WebBridgeClient()
        self.guard = SafetyGuard()
        self.extracted_today = 0
    
    def _extract_from_search_page(self) -> List[dict]:
        """
        Extract prospect cards from current search results page.
        Uses JavaScript evaluation to parse the DOM.
        """
        extraction_js = """
        (() => {
            const prospects = [];
            const seen = new Set();
            
            // LinkedIn search results use various selectors over time
            // Try multiple patterns
            const selectors = [
                'div.entity-result__content',  // Classic
                'li.reusable-search__result-container',
                'div.search-result__info',
                '[data-test-id="search-result"]',
                '.artdeco-entity-lockup__content'
            ];
            
            let cards = [];
            for (const sel of selectors) {
                const found = document.querySelectorAll(sel);
                if (found.length > 0) {
                    cards = Array.from(found);
                    break;
                }
            }
            
            // Fallback: find all links that look like profile links
            if (cards.length === 0) {
                const allLinks = document.querySelectorAll('a[href*="/in/"]');
                const linkMap = new Map();
                for (const link of allLinks) {
                    const href = link.getAttribute('href');
                    if (!href || href.includes('translate')) continue;
                    const base = href.split('?')[0];
                    if (!linkMap.has(base)) {
                        linkMap.set(base, link);
                    }
                }
                cards = Array.from(linkMap.values());
            }
            
            for (const card of cards) {
                try {
                    let name = '';
                    let title = '';
                    let company = '';
                    let location = '';
                    let profile_url = '';
                    
                    // Try to find profile URL
                    const link = card.closest ? 
                        card.closest('a[href*="/in/"]') || 
                        card.querySelector('a[href*="/in/"]') :
                        card;
                    
                    if (link) {
                        let href = link.getAttribute('href') || '';
                        if (href.includes('/in/')) {
                            profile_url = 'https://www.linkedin.com' + href.split('?')[0];
                        }
                    }
                    
                    // Extract name - look for headings or spans with name-like text
                    const nameSelectors = [
                        '.entity-result__title-text a span span',
                        '.artdeco-entity-lockup__title span',
                        'span[dir="ltr"]',
                        'span[aria-hidden="true"]'
                    ];
                    
                    for (const sel of nameSelectors) {
                        const el = card.querySelector ? card.querySelector(sel) : null;
                        if (el && el.textContent.trim().length > 2 && !el.textContent.includes('LinkedIn')) {
                            name = el.textContent.trim().split('\\n')[0].trim();
                            if (name.length > 0) break;
                        }
                    }
                    
                    // If still no name, try the link text
                    if (!name && link) {
                        name = link.textContent.trim().split('\\n')[0].trim();
                    }
                    
                    // Extract subtitle (usually title + company)
                    const subtitleSelectors = [
                        '.entity-result__primary-subtitle',
                        '.artdeco-entity-lockup__subtitle',
                        '.search-result__truncate'
                    ];
                    
                    for (const sel of subtitleSelectors) {
                        const el = card.querySelector ? card.querySelector(sel) : null;
                        if (el) {
                            const text = el.textContent.trim();
                            if (text.includes(' at ')) {
                                const parts = text.split(' at ');
                                title = parts[0].trim();
                                company = parts[1].trim();
                            } else if (text.includes(' | ')) {
                                const parts = text.split(' | ');
                                title = parts[0].trim();
                                company = parts[1].trim();
                            } else {
                                title = text;
                            }
                            break;
                        }
                    }
                    
                    // Extract location
                    const locSelectors = [
                        '.entity-result__secondary-subtitle',
                        '.artdeco-entity-lockup__caption'
                    ];
                    
                    for (const sel of locSelectors) {
                        const el = card.querySelector ? card.querySelector(sel) : null;
                        if (el) {
                            location = el.textContent.trim();
                            break;
                        }
                    }
                    
                    // Clean up
                    name = name.replace(/\\s+/g, ' ').trim();
                    title = title.replace(/\\s+/g, ' ').trim();
                    company = company.replace(/\\s+/g, ' ').trim();
                    location = location.replace(/\\s+/g, ' ').trim();
                    
                    // Deduplicate by URL
                    if (profile_url && !seen.has(profile_url) && name.length > 1) {
                        seen.add(profile_url);
                        prospects.push({
                            name,
                            title,
                            company,
                            location,
                            profile_url,
                            source_page: window.location.href
                        });
                    }
                } catch (e) {
                    // Skip problematic cards
                }
            }
            
            return JSON.stringify(prospects);
        })()
        """
        
        result = self.wb.evaluate(extraction_js)
        if not result.get("ok"):
            print(f"  ⚠️  Extraction error: {result.get('error', 'unknown')}")
            return []
        
        try:
            data = json.loads(result.get("data", {}).get("value", "[]"))
            if isinstance(data, str):
                data = json.loads(data)
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"  ⚠️  Parse error: {e}")
            return []
    
    def search_and_extract(self, keywords: List[str], geo_urn: str = None, 
                           geo_name: str = "", max_pages: int = None) -> List[dict]:
        """
        Perform a LinkedIn search and extract prospects from result pages.
        """
        max_pages = max_pages or SAFETY["max_pages_per_search"]
        all_prospects = []
        
        if not self.guard.can_search():
            print("❌ Daily search limit reached. Stopping.")
            return all_prospects
        
        # Build and navigate to search URL
        search_url = LinkedInSearchBuilder.build_url(keywords, geo_urn=geo_urn)
        print(f"\n🔍 Searching: {' '.join(keywords)} {f'in {geo_name}' if geo_name else ''}")
        print(f"   URL: {search_url[:100]}...")
        
        result = self.wb.navigate(search_url, new_tab=True)
        if not result.get("ok"):
            print(f"❌ Navigation failed: {result}")
            return all_prospects
        
        self.guard.human_delay(5, 8)  # Wait for page load
        self.guard.record_search()
        
        # Extract from multiple pages
        for page in range(1, max_pages + 1):
            print(f"\n  📄 Page {page}")
            
            # Scroll to load all results
            self.wb.scroll_to_bottom()
            self.guard.human_delay(2, 4)
            
            # Extract prospects
            prospects = self._extract_from_search_page()
            
            if not prospects:
                print(f"    No prospects found on page {page}. Ending search.")
                break
            
            # Deduplicate against already extracted
            new_prospects = []
            for p in prospects:
                if not any(p.get("profile_url") == existing.get("profile_url") 
                          for existing in all_prospects):
                    new_prospects.append(p)
            
            print(f"    Found {len(prospects)} cards, {len(new_prospects)} new")
            all_prospects.extend(new_prospects)
            self.guard.record_extraction(len(new_prospects))
            
            # Check if we've hit the daily limit
            if not self.guard.can_extract_more(10):
                print("⚠️  Approaching daily extraction limit. Stopping.")
                break
            
            # Navigate to next page
            if page < max_pages:
                next_url = LinkedInSearchBuilder.build_url(keywords, geo_urn=geo_urn, page=page + 1)
                self.wb.navigate(next_url)
                self.guard.human_delay(4, 7)
        
        print(f"\n✅ Search complete. Total new prospects: {len(all_prospects)}")
        return all_prospects
    
    def run_all_searches(self) -> List[dict]:
        """Run all predefined searches."""
        configs = LinkedInSearchBuilder.get_all_search_configs()
        all_prospects = []
        
        print(f"\n{'='*60}")
        print("Q-MOL LINKEDIN PROSPECT EXTRACTION")
        print(f"{'='*60}")
        print(f"Total search configs: {len(configs)}")
        print(f"Daily limit: {SAFETY['max_profile_views_per_day']} profiles")
        self.guard.print_status()
        
        for i, config in enumerate(configs, 1):
            if not self.guard.can_search() or not self.guard.can_extract_more(10):
                print("\n⛔ Daily limits reached. Stopping.")
                break
            
            print(f"\n[{i}/{len(configs)}] {config['label']}")
            prospects = self.search_and_extract(
                config["keywords"],
                geo_urn=config.get("geo_urn"),
                geo_name=config.get("geo_name"),
                max_pages=3  # Limit pages per search to spread across queries
            )
            all_prospects.extend(prospects)
            
            # Safety delay between searches
            if i < len(configs):
                self.guard.human_delay(15, 30)
        
        return all_prospects
    
    def save_prospects(self, prospects: List[dict], filename: str = None):
        """Save prospects to CSV."""
        if not prospects:
            print("No prospects to save.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"prospects_raw_{timestamp}.csv"
        filepath = OUTPUT_DIR / filename
        
        # Add metadata fields
        for p in prospects:
            p["extracted_at"] = datetime.now().isoformat()
            p["status"] = "new"
            p["score"] = 0
            p["notes"] = ""
        
        fieldnames = ["name", "title", "company", "location", 
                      "profile_url", "source_page", "extracted_at", 
                      "status", "score", "notes"]
        
        # Check for existing file and append
        mode = "a" if filepath.exists() else "w"
        write_header = not filepath.exists()
        
        with open(filepath, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(prospects)
        
        print(f"\n💾 Saved {len(prospects)} prospects to: {filepath}")
        return filepath


# ---------------------------------------------------------------------------
# Prospect Scorer & Filter
# ---------------------------------------------------------------------------

class ProspectScorer:
    """Scores prospects based on relevance to Q-Mol."""
    
    HIGH_VALUE_KEYWORDS = {
        "title": [
            "cheminformatic", "computational chemist", "medicinal chemist",
            "drug discovery", "virtual screening", "molecular model",
            "CADD", "ADMET", "QSAR", "docking", "RDKit",
            "pharmaceutical", "biotech", "pharma",
            "AI drug", "machine learning", "deep learning",
            "compound library", "hit identification", "lead optimization",
            "bioinformatic", "data scientist", "ML engineer",
            "director", "head of", "CTO", "CSO", "VP",
            "founder", "CEO", "chief scientific"
        ],
        "company": [
            "biotech", "pharma", "pharmaceutical", "drug discovery",
            "CRO", "medicinal", "chemistry", "AI", "insilico",
            "atomwise", "recursion", "relay", "schrödinger",
            "benevolent", "exscientia", "insitro"
        ]
    }
    
    @classmethod
    def score_prospect(cls, prospect: dict) -> int:
        """Calculate relevance score for a prospect."""
        score = 0
        title = (prospect.get("title", "") + " " + prospect.get("name", "")).lower()
        company = prospect.get("company", "").lower()
        
        # Title keywords
        for kw in cls.HIGH_VALUE_KEYWORDS["title"]:
            if kw.lower() in title:
                score += CONFIG["scoring_weights"]["title_keyword_match"]
        
        # Company keywords
        for kw in cls.HIGH_VALUE_KEYWORDS["company"]:
            if kw.lower() in company:
                score += CONFIG["scoring_weights"]["company_size_match"]
        
        # Location bonus for target markets
        location = prospect.get("location", "").lower()
        target_locations = ["united states", "united kingdom", "germany", 
                           "switzerland", "canada", "boston", "san francisco",
                           "san diego", "cambridge", "london", "basel"]
        for loc in target_locations:
            if loc in location:
                score += CONFIG["scoring_weights"]["location_match"]
                break
        
        return min(score, 100)  # Cap at 100
    
    @classmethod
    def process_csv(cls, input_path: Path, output_path: Path = None):
        """Score all prospects in a CSV file."""
        output_path = output_path or input_path.parent / input_path.name.replace(".csv", "_scored.csv")
        
        prospects = []
        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prospects = list(reader)
        
        for p in prospects:
            p["score"] = cls.score_prospect(p)
        
        # Sort by score descending
        prospects.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
        
        fieldnames = list(prospects[0].keys()) if prospects else []
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(prospects)
        
        # Print summary
        high_score = sum(1 for p in prospects if int(p.get("score", 0)) >= 30)
        medium_score = sum(1 for p in prospects if 15 <= int(p.get("score", 0)) < 30)
        
        print(f"\n📊 Scoring Complete: {input_path.name}")
        print(f"   Total prospects: {len(prospects)}")
        print(f"   High score (≥30): {high_score}")
        print(f"   Medium score (15-29): {medium_score}")
        print(f"   Saved to: {output_path}")
        
        return output_path


# ---------------------------------------------------------------------------
# Profile Deep Extractor (Optional - for high-value prospects)
# ---------------------------------------------------------------------------

class ProfileDeepExtractor:
    """
    Extracts additional details from individual LinkedIn profiles.
    USE WITH EXTREME CAUTION - visits individual profiles.
    """
    
    def __init__(self):
        self.wb = WebBridgeClient()
        self.guard = SafetyGuard()
    
    def extract_profile_details(self, profile_url: str) -> dict:
        """Extract details from a single profile page."""
        if not self.guard.can_view_profile():
            print("❌ Daily profile view limit reached.")
            return {}
        
        print(f"  🔎 Visiting: {profile_url}")
        result = self.wb.navigate(profile_url, new_tab=True)
        if not result.get("ok"):
            return {}
        
        self.guard.human_delay(4, 7)
        self.guard.record_profile_view()
        
        # Extract headline, about section, experience
        extraction_js = """
        (() => {
            const data = {};
            
            // Headline
            const headline = document.querySelector('.text-body-medium');
            if (headline) data.headline = headline.textContent.trim();
            
            // About section
            const about = document.querySelector('.pv-about__summary-text, .inline-show-more-text');
            if (about) data.about = about.textContent.trim().substring(0, 500);
            
            // Current company from experience
            const expItems = document.querySelectorAll('li.artdeco-list__item');
            const companies = [];
            for (const item of expItems.slice(0, 3)) {
                const companyEl = item.querySelector('.t-14.t-normal');
                if (companyEl) companies.push(companyEl.textContent.trim());
            }
            if (companies.length > 0) data.recent_companies = companies.join('; ');
            
            return JSON.stringify(data);
        })()
        """
        
        result = self.wb.evaluate(extraction_js)
        details = {}
        if result.get("ok"):
            try:
                details = json.loads(result.get("data", {}).get("value", "{}"))
                if isinstance(details, str):
                    details = json.loads(details)
            except:
                pass
        
        self.guard.profile_delay()
        return details
    
    def process_high_value_prospects(self, input_csv: Path, limit: int = 10):
        """Enrich top prospects with profile details."""
        prospects = []
        with open(input_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prospects = list(reader)
        
        # Sort by score and take top N
        prospects.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
        top_prospects = prospects[:limit]
        
        print(f"\n🎯 Enriching top {len(top_prospects)} prospects...")
        
        for p in top_prospects:
            url = p.get("profile_url", "")
            if not url:
                continue
            
            details = self.extract_profile_details(url)
            if details:
                p["headline"] = details.get("headline", "")
                p["about_snippet"] = details.get("about", "")
                p["recent_companies"] = details.get("recent_companies", "")
                print(f"  ✅ Enriched: {p.get('name', '')}")
            else:
                print(f"  ⚠️  Failed: {p.get('name', '')}")
        
        # Save enriched data
        output_path = input_csv.parent / input_csv.name.replace(".csv", "_enriched.csv")
        fieldnames = list(prospects[0].keys()) if prospects else []
        
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(prospects)
        
        print(f"\n💾 Enriched data saved to: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Q-Mol LinkedIn Prospect Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all predefined searches
  python linkedin_prospect_extractor.py --search-all

  # Search with custom keywords
  python linkedin_prospect_extractor.py --search "computational chemistry drug discovery"

  # Score existing prospects
  python linkedin_prospect_extractor.py --score-prospects --input data/linkedin/prospects_raw_20250705.csv

  # Enrich top prospects (visits profiles - use sparingly!)
  python linkedin_prospect_extractor.py --enrich-profiles --input prospects_scored.csv --limit 5

  # Check daily status
  python linkedin_prospect_extractor.py --status
        """
    )
    
    parser.add_argument("--search-all", action="store_true",
                        help="Run all predefined searches")
    parser.add_argument("--search", type=str,
                        help="Search with custom keywords")
    parser.add_argument("--geo", type=str, default="",
                        help="Filter by geography (e.g., 'United States')")
    parser.add_argument("--pages", type=int, default=3,
                        help="Max pages per search (default: 3)")
    parser.add_argument("--score-prospects", action="store_true",
                        help="Score prospects by relevance")
    parser.add_argument("--input", type=str,
                        help="Input CSV file for scoring/enrichment")
    parser.add_argument("--enrich-profiles", action="store_true",
                        help="Enrich top prospects with profile details")
    parser.add_argument("--limit", type=int, default=10,
                        help="Limit for enrichment (default: 10)")
    parser.add_argument("--status", action="store_true",
                        help="Show daily safety status")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                        help="Output directory for CSV files")
    
    args = parser.parse_args()
    
    # Show status
    if args.status or len(sys.argv) == 1:
        guard = SafetyGuard()
        guard.print_status()
        print("\nRun with --help for usage information.")
        return
    
    # Score prospects
    if args.score_prospects:
        if not args.input:
            print("❌ Error: --input required for scoring")
            sys.exit(1)
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ File not found: {input_path}")
            sys.exit(1)
        ProspectScorer.process_csv(input_path)
        return
    
    # Enrich profiles
    if args.enrich_profiles:
        if not args.input:
            print("❌ Error: --input required for enrichment")
            sys.exit(1)
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ File not found: {input_path}")
            sys.exit(1)
        extractor = ProfileDeepExtractor()
        extractor.process_high_value_prospects(input_path, limit=args.limit)
        return
    
    # Search operations
    extractor = ProspectExtractor()
    
    if args.search_all:
        print("🚀 Running all predefined searches...")
        prospects = extractor.run_all_searches()
        if prospects:
            extractor.save_prospects(prospects, "prospects_raw_batch.csv")
        extractor.guard.print_status()
    
    elif args.search:
        keywords = args.search.split()
        geo_urn = None
        geo_name = ""
        
        # Look up geo URN if specified
        if args.geo:
            for geo in CONFIG["search_targets"]["geographies"]:
                if geo["name"].lower() == args.geo.lower():
                    geo_urn = geo["urn"]
                    geo_name = geo["name"]
                    break
        
        prospects = extractor.search_and_extract(
            keywords, geo_urn=geo_urn, geo_name=geo_name, max_pages=args.pages
        )
        if prospects:
            extractor.save_prospects(prospects)
        extractor.guard.print_status()


if __name__ == "__main__":
    main()
