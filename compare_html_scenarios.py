#!/usr/bin/env python3
"""Compare HTML between successful scraping (with odds/scores) vs unsuccessful (names only)"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper import HardRockScraper

def test_successful_vs_unsuccessful_scraping():
    """Test both scenarios and save HTML for comparison"""
    print("🔍 Testing successful vs unsuccessful scraping scenarios...")
    
    # Test Czech Liga Pro (was working locally, failing in production)
    test_url = "https://app.hardrock.bet/sport-leagues/table_tennis/767397703555776513"
    
    print(f"📥 Testing URL: {test_url}")
    
    # Test with different configurations
    scenarios = [
        ("local_headless_false", {"headless": False}),
        ("local_headless_true", {"headless": True}),
        ("production_like", {"headless": True}),  # Same as production
    ]
    
    for scenario_name, config in scenarios:
        print(f"\n🧪 Testing scenario: {scenario_name}")
        
        scraper = HardRockScraper(
            base_url=test_url,
            headless=config["headless"],
            auto_store=False
        )
        
        try:
            # Get matches
            matches = scraper.get_matches()
            html_content = scraper.last_html
            
            # Save HTML
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"html_comparison_{scenario_name}_{timestamp}.html"
            
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Analyze results
            print(f"   📊 Found {len(matches)} matches")
            print(f"   📄 HTML size: {len(html_content):,} characters")
            print(f"   💾 Saved to: {html_filename}")
            
            # Check HTML content
            has_hr_market_view = "hr-market-view" in html_content
            has_selection_odds = "selection-odds" in html_content
            has_score_container = "scoreContainer" in html_content
            has_live_icon = "live-icon" in html_content
            
            print(f"   🔍 HTML Analysis:")
            print(f"      .hr-market-view: {has_hr_market_view}")
            print(f"      .selection-odds: {has_selection_odds}")
            print(f"      .scoreContainer: {has_score_container}")
            print(f"      .live-icon: {has_live_icon}")
            
            # Analyze matches
            if matches:
                first_match = matches[0]
                print(f"   📋 First match:")
                print(f"      Players: {first_match.player1.name} vs {first_match.player2.name}")
                print(f"      Status: {first_match.status}")
                print(f"      Has Odds: {first_match.odds is not None}")
                print(f"      Has Score: {first_match.score is not None}")
                
                if first_match.odds:
                    print(f"      Odds: {first_match.odds.player1_moneyline}|{first_match.odds.player2_moneyline}")
                if first_match.score:
                    print(f"      Score: {first_match.score}")
            
            # Save a snippet of HTML around key elements
            snippet_file = f"html_snippet_{scenario_name}_{timestamp}.txt"
            with open(snippet_file, 'w', encoding='utf-8') as f:
                f.write(f"=== HTML Analysis for {scenario_name} ===\n\n")
                
                # Find first hr-market-view container
                if "hr-market-view" in html_content:
                    start_idx = html_content.find('class="hr-market-view"')
                    if start_idx != -1:
                        # Go back to find the opening tag
                        search_start = max(0, start_idx - 200)
                        snippet_start = html_content.rfind('<', search_start, start_idx)
                        if snippet_start == -1:
                            snippet_start = start_idx
                        
                        # Find the end of this container (simplified)
                        snippet_end = min(len(html_content), start_idx + 3000)
                        
                        snippet = html_content[snippet_start:snippet_end]
                        f.write("First .hr-market-view container:\n")
                        f.write(snippet)
                        f.write("\n\n")
                
                # Count key elements
                f.write("Element counts:\n")
                f.write(f".hr-market-view: {html_content.count('hr-market-view')}\n")
                f.write(f".selection-odds: {html_content.count('selection-odds')}\n")
                f.write(f".selection-container: {html_content.count('selection-container')}\n")
                f.write(f".scoreContainer: {html_content.count('scoreContainer')}\n")
                f.write(f".live-icon: {html_content.count('live-icon')}\n")
                f.write(f"data-tooltip-id: {html_content.count('data-tooltip-id')}\n")
            
            print(f"   📝 Snippet saved to: {snippet_file}")
            
        except Exception as e:
            print(f"   ❌ Error in {scenario_name}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            scraper.close()
    
    print("\n🎯 Comparison complete! Check the generated files to compare HTML differences.")

if __name__ == "__main__":
    test_successful_vs_unsuccessful_scraping()