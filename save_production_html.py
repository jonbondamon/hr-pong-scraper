#!/usr/bin/env python3
"""Save HTML from production scraper for comparison"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper import HardRockScraper

def save_html_for_debugging():
    """Save HTML content from production-like scraper"""
    print("🔍 Saving HTML from production-like scraper...")
    
    # Use production settings
    scraper = HardRockScraper(
        base_url="https://app.hardrock.bet/sport-leagues/table_tennis/767397703555776513",
        headless=True,  # Same as production
        auto_store=False
    )
    
    try:
        print("📥 Loading page (headless, like production)...")
        matches = scraper.get_matches()
        html_content = scraper.last_html
        
        # Save HTML with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"production_debug_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 Saved HTML to {filename}")
        print(f"📊 Found {len(matches)} matches")
        
        if matches:
            # Show first match details
            first_match = matches[0]
            print(f"\n📋 First match from production-like scraper:")
            print(f"   Match ID: {first_match.match_id}")
            print(f"   Players: {first_match.player1.name} vs {first_match.player2.name}")
            print(f"   Status: {first_match.status}")
            print(f"   Odds: {first_match.odds}")
            print(f"   Score: {first_match.score}")
            print(f"   League: {first_match.league}")
        
        # Check HTML size and content
        print(f"\n📄 HTML Statistics:")
        print(f"   Size: {len(html_content):,} characters")
        print(f"   Contains .hr-market-view: {'hr-market-view' in html_content}")
        print(f"   Contains .selection-odds: {'selection-odds' in html_content}")
        print(f"   Contains selection-container: {'selection-container' in html_content}")
        
        # Look for specific content that indicates full loading
        if '-' in html_content and '+' in html_content:
            print(f"   ✅ Contains odds-like content (+ and - symbols)")
        else:
            print(f"   ❌ Missing odds-like content")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    save_html_for_debugging()