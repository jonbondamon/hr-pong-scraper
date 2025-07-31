#!/usr/bin/env python3
"""Run multi-league scraper with Cosmos DB storage"""

import sys
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from multi_league_scraper import MultiLeagueScraper
from hardrock_scraper.cosmos_client import CosmosDBClient


def run_scraper_with_cosmos():
    """Run scraper with Cosmos DB integration"""
    
    print("🏓 HardRock Multi-League Scraper with Cosmos DB")
    print("=" * 50)
    
    # Initialize Cosmos DB client
    print("🌟 Initializing Cosmos DB client...")
    cosmos_client = CosmosDBClient()
    print(f"✅ Connected to: {cosmos_client.database_name}/{cosmos_client.container_name}")
    
    # Initialize multi-scraper with Cosmos DB
    print("\n🚀 Initializing multi-league scraper...")
    multi_scraper = MultiLeagueScraper(cosmos_client=cosmos_client, headless=True)
    multi_scraper.initialize_scrapers()
    
    try:
        # Scrape all leagues and store to Cosmos DB
        print("\n📊 Starting scraping with automatic Cosmos DB storage...")
        results = multi_scraper.scrape_all_leagues()
        
        # Print summary
        multi_scraper.print_summary()
        
        # Get Cosmos DB stats after storage
        print("\n💾 Cosmos DB Storage Results:")
        cosmos_stats = cosmos_client.get_container_stats()
        print(f"   Documents in container: {cosmos_stats.get('total_matches', 0)}")
        print(f"   Live matches stored: {cosmos_stats.get('live_matches', 0)}")
        print(f"   Upcoming matches stored: {cosmos_stats.get('upcoming_matches', 0)}")
        
        # Show some sample historical data structure
        if cosmos_stats.get('total_matches', 0) > 0:
            print("\n🔍 Sample Historical Document Structure:")
            # Get first match for inspection
            live_matches = cosmos_client.get_live_matches()
            if live_matches:
                sample_match = live_matches[0]
                print(f"   Match: {sample_match.get('player1', {}).get('name')} vs {sample_match.get('player2', {}).get('name')}")
                print(f"   Score History Entries: {len(sample_match.get('score_history', []))}")
                print(f"   Odds History Entries: {len(sample_match.get('odds_history', []))}")
                print(f"   Status History Entries: {len(sample_match.get('status_history', []))}")
        
        print(f"\n✅ Scraping with Cosmos DB storage completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        multi_scraper.close_all()


if __name__ == "__main__":
    run_scraper_with_cosmos()