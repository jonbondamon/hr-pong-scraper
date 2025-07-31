#!/usr/bin/env python3
"""Debug the parser to see what HTML structure we're working with"""

import sys
import os
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper import HardRockScraper

def main():
    """Debug parser by examining HTML structure"""
    print("🔍 Debugging HTML parser...")
    
    # Create scraper for one league
    scraper = HardRockScraper(
        base_url="https://app.hardrock.bet/sport-leagues/table_tennis/767397703555776513",
        headless=True,
        auto_store=False
    )
    
    try:
        # Get HTML content
        print("📥 Loading page...")
        matches = scraper.get_matches()  # This will initialize driver and get content
        html_content = scraper.last_html
        
        # Save HTML for inspection
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("💾 Saved HTML to debug_page_source.html")
        
        print(f"📊 Found {len(matches)} matches")
        
        if matches:
            # Examine first match in detail
            first_match = matches[0]
            print(f"\n📋 First match details:")
            print(f"   Match ID: {first_match.match_id}")
            print(f"   Player 1: {first_match.player1.name}")
            print(f"   Player 2: {first_match.player2.name}")
            print(f"   Status: {first_match.status}")
            print(f"   Score: {first_match.score}")
            print(f"   Odds: {first_match.odds}")
            print(f"   League: {first_match.league}")
            
            # Convert to dict to see full structure
            match_dict = first_match.to_dict()
            print(f"\n📄 Full match data:")
            import json
            print(json.dumps(match_dict, indent=2, default=str))
        
        # Let's also examine the HTML structure
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find match containers
        containers = soup.select('.hr-market-view')
        print(f"\n🔍 Found {len(containers)} .hr-market-view containers")
        
        if containers:
            # Examine first container
            first_container = containers[0]
            print(f"\n📋 First container HTML (first 500 chars):")
            print(first_container.prettify()[:500] + "...")
            
            # Look for odds elements
            odds_elements = first_container.select('.selection-odds')
            print(f"\n💰 Found {len(odds_elements)} .selection-odds elements")
            for i, elem in enumerate(odds_elements[:3]):
                print(f"   Odds {i+1}: {elem.get_text(strip=True)}")
            
            # Look for selection containers
            selection_containers = first_container.select('.selection-container')
            print(f"\n🎯 Found {len(selection_containers)} .selection-container elements")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()