#!/usr/bin/env python3
"""Multi-league HardRock scraper for all table tennis leagues"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper import HardRockScraper
from hardrock_scraper.cosmos_client import CosmosDBClient
from hardrock_scraper.models import Match


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiLeagueScraper:
    """Scraper for multiple HardRock table tennis leagues"""
    
    LEAGUE_URLS = {
        "Czech Liga Pro": "https://app.hardrock.bet/sport-leagues/table_tennis/767397703555776513",
        "TT Cup": "https://app.hardrock.bet/sport-leagues/table_tennis/691030508749717506", 
        "TT Elite Series": "https://app.hardrock.bet/sport-leagues/table_tennis/754964912222535699",
        "TT Star Series": "https://app.hardrock.bet/sport-leagues/table_tennis/7406140231619706928"
    }
    
    def __init__(self, cosmos_client: Optional[CosmosDBClient] = None, headless: bool = True):
        self.cosmos_client = cosmos_client
        self.headless = headless
        self.scrapers: Dict[str, HardRockScraper] = {}
        self.all_matches: List[Match] = []
        
    def initialize_scrapers(self):
        """Initialize individual scrapers for each league"""
        for league_name, url in self.LEAGUE_URLS.items():
            logger.info(f"Initializing scraper for {league_name}")
            
            scraper = HardRockScraper(
                base_url=url,
                headless=self.headless,
                cosmos_client=self.cosmos_client,
                auto_store=True  # Auto-store to Cosmos DB
            )
            
            self.scrapers[league_name] = scraper
            
        logger.info(f"Initialized {len(self.scrapers)} league scrapers")
    
    def scrape_all_leagues(self) -> Dict[str, List[Match]]:
        """Scrape all leagues and return matches by league"""
        results = {}
        
        for league_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Scraping {league_name}...")
                matches = scraper.get_matches()
                
                # Add league info to matches
                for match in matches:
                    match.league = league_name
                
                results[league_name] = matches
                logger.info(f"{league_name}: Found {len(matches)} matches")
                
                # Add to combined list
                self.all_matches.extend(matches)
                
            except Exception as e:
                logger.error(f"Error scraping {league_name}: {e}")
                results[league_name] = []
        
        return results
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics across all leagues"""
        total_matches = len(self.all_matches)
        live_matches = sum(1 for m in self.all_matches if m.is_live())
        upcoming_matches = sum(1 for m in self.all_matches if m.is_upcoming())
        
        league_stats = {}
        for league_name, scraper in self.scrapers.items():
            league_matches = [m for m in self.all_matches if m.league == league_name]
            league_stats[league_name] = {
                'total': len(league_matches),
                'live': sum(1 for m in league_matches if m.is_live()),
                'upcoming': sum(1 for m in league_matches if m.is_upcoming())
            }
        
        return {
            'total_matches': total_matches,
            'live_matches': live_matches,
            'upcoming_matches': upcoming_matches,
            'league_breakdown': league_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print a formatted summary of scraped data"""
        stats = self.get_summary_stats()
        
        print("\n" + "="*60)
        print("🏓 HARDROCK TABLE TENNIS SCRAPING SUMMARY")
        print("="*60)
        print(f"📊 Total Matches: {stats['total_matches']}")
        print(f"🔴 Live Matches: {stats['live_matches']}")
        print(f"⏳ Upcoming Matches: {stats['upcoming_matches']}")
        print(f"⏰ Scraped at: {stats['timestamp']}")
        
        print("\n📋 League Breakdown:")
        for league, data in stats['league_breakdown'].items():
            print(f"  {league}:")
            print(f"    Total: {data['total']}, Live: {data['live']}, Upcoming: {data['upcoming']}")
        
        # Show some live matches if available
        live_matches = [m for m in self.all_matches if m.is_live()]
        if live_matches:
            print(f"\n🔴 Live Matches ({len(live_matches)}):")
            for match in live_matches[:5]:  # Show first 5
                score_str = f" - {match.score}" if match.score else ""
                odds_str = f" [{match.odds.player1_moneyline}|{match.odds.player2_moneyline}]" if match.odds else ""
                print(f"  [{match.league}] {match.player1.name} vs {match.player2.name}{score_str}{odds_str}")
            
            if len(live_matches) > 5:
                print(f"  ... and {len(live_matches) - 5} more")
    
    def close_all(self):
        """Close all scrapers"""
        for scraper in self.scrapers.values():
            scraper.close()


def main():
    """Main function for testing multi-league scraper"""
    
    # For testing, we'll run without Cosmos DB
    print("🏓 Multi-League HardRock Table Tennis Scraper")
    print("=" * 50)
    
    # Initialize scraper
    multi_scraper = MultiLeagueScraper(headless=True)
    
    try:
        # Initialize all league scrapers
        multi_scraper.initialize_scrapers()
        
        # Scrape all leagues
        print("\n🚀 Starting multi-league scraping...")
        start_time = time.time()
        
        results = multi_scraper.scrape_all_leagues()
        
        end_time = time.time()
        scrape_duration = end_time - start_time
        
        # Print summary
        multi_scraper.print_summary()
        
        print(f"\n⏱️  Scraping completed in {scrape_duration:.2f} seconds")
        
        # Export results
        import json
        export_data = {
            'scrape_time': datetime.now().isoformat(),
            'duration_seconds': scrape_duration,
            'summary': multi_scraper.get_summary_stats(),
            'matches': [match.to_dict() for match in multi_scraper.all_matches]
        }
        
        with open('multi_league_results.json', 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"📁 Results exported to: multi_league_results.json")
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        multi_scraper.close_all()


if __name__ == "__main__":
    main()