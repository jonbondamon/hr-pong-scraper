"""Basic usage examples for HardRock table tennis scraper"""

import logging
from hardrock_scraper import HardRockScraper

# Configure logging
logging.basicConfig(level=logging.INFO)

def basic_scraping_example():
    """Simple one-time scraping example"""
    
    # Replace with actual HardRock table tennis URL
    url = "https://sportsbook.hardrocknj.com/en-us/betting/table-tennis"
    
    # Create scraper instance
    with HardRockScraper(url, headless=True) as scraper:
        # Get all current matches
        matches = scraper.get_matches()
        
        print(f"Found {len(matches)} matches:")
        for match in matches:
            print(f"  {match}")
            
            # Print odds if available
            if match.odds:
                print(f"    Odds: {match.odds.player1_moneyline} | {match.odds.player2_moneyline}")
            
            # Print score if live
            if match.score:
                print(f"    Score: {match.score}")
            
            print()

def live_matches_only():
    """Get only live matches"""
    
    url = "https://sportsbook.hardrocknj.com/en-us/betting/table-tennis"
    
    with HardRockScraper(url) as scraper:
        live_matches = scraper.get_live_matches()
        
        print(f"Live matches ({len(live_matches)}):")
        for match in live_matches:
            print(f"  {match}")

def upcoming_matches_only():
    """Get only upcoming matches"""
    
    url = "https://sportsbook.hardrocknj.com/en-us/betting/table-tennis"
    
    with HardRockScraper(url) as scraper:
        upcoming_matches = scraper.get_upcoming_matches()
        
        print(f"Upcoming matches ({len(upcoming_matches)}):")
        for match in upcoming_matches:
            print(f"  {match}")
            if match.start_time:
                print(f"    Starts: {match.start_time}")

def find_specific_match():
    """Find a specific match by player names"""
    
    url = "https://sportsbook.hardrocknj.com/en-us/betting/table-tennis"
    
    with HardRockScraper(url) as scraper:
        # Look for a match between specific players
        match = scraper.get_match_by_players("Player A", "Player B")
        
        if match:
            print(f"Found match: {match}")
            print(f"  Status: {match.status.value}")
            if match.odds:
                print(f"  Odds: {match.odds.player1_moneyline} | {match.odds.player2_moneyline}")
        else:
            print("Match not found")

def custom_configuration():
    """Example with custom configuration"""
    
    url = "https://sportsbook.hardrocknj.com/en-us/betting/table-tennis"
    
    # Custom scraper settings
    scraper = HardRockScraper(
        base_url=url,
        headless=False,  # Show browser for debugging
        live_refresh_interval=10,  # Refresh live matches every 10 seconds
        upcoming_refresh_interval=300,  # Refresh upcoming every 5 minutes
        full_refresh_timeout=600  # Full page refresh every 10 minutes
    )
    
    try:
        matches = scraper.get_matches()
        print(f"Found {len(matches)} matches with custom settings")
        
        for match in matches:
            # Convert to dictionary for easy serialization
            match_dict = match.to_dict()
            print(f"Match data: {match_dict}")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    print("=== Basic Scraping ===")
    basic_scraping_example()
    
    print("\n=== Live Matches Only ===")
    live_matches_only()
    
    print("\n=== Upcoming Matches Only ===")
    upcoming_matches_only()
    
    print("\n=== Find Specific Match ===")
    find_specific_match()
    
    print("\n=== Custom Configuration ===")
    custom_configuration()