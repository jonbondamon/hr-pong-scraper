#!/usr/bin/env python3
"""Test production behavior locally"""

import sys
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper.cosmos_client import CosmosDBClient
from multi_league_scraper import MultiLeagueScraper

def test_single_league():
    """Test a single league to see if data is being stored correctly"""
    print("🔍 Testing single league scraper behavior...")
    
    # Initialize Cosmos DB client
    cosmos_client = CosmosDBClient()
    
    # Initialize single league scraper (Czech Liga Pro)
    multi_scraper = MultiLeagueScraper(
        cosmos_client=cosmos_client,
        headless=True
    )
    
    # Only test one league to save time
    test_league = "Czech Liga Pro"
    test_url = "https://app.hardrock.bet/sport-leagues/table_tennis/767397703555776513"
    
    multi_scraper.LEAGUE_URLS = {test_league: test_url}
    
    try:
        # Initialize scrapers
        multi_scraper.initialize_scrapers()
        
        # Scrape the test league
        print(f"🚀 Scraping {test_league}...")
        results = multi_scraper.scrape_all_leagues()
        
        # Get matches for this league
        matches = results.get(test_league, [])
        print(f"📊 Found {len(matches)} matches")
        
        if matches:
            # Examine first match
            first_match = matches[0]
            print(f"\n📋 First match details:")
            print(f"   Match ID: {first_match.match_id}")
            print(f"   Player 1: {first_match.player1.name}")
            print(f"   Player 2: {first_match.player2.name}")
            print(f"   Status: {first_match.status}")
            print(f"   League: {first_match.league}")  # Should be set to test_league
            print(f"   Score: {first_match.score}")
            print(f"   Odds: {first_match.odds}")
            
            # Check what was stored in Cosmos DB
            print(f"\n🔍 Checking Cosmos DB storage...")
            stored_doc = cosmos_client.get_match(first_match.match_id)
            if stored_doc:
                print(f"   Stored League: {stored_doc.get('league')}")
                print(f"   Stored Odds: {stored_doc.get('odds')}")
                print(f"   Stored Score: {stored_doc.get('score')}")
            else:
                print(f"   ❌ Document not found in Cosmos DB!")
        
        multi_scraper.close_all()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        multi_scraper.close_all()

if __name__ == "__main__":
    test_single_league()