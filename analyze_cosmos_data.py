#!/usr/bin/env python3
"""Analyze Cosmos DB data to understand what's missing"""

import sys
import json
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper.cosmos_client import CosmosDBClient

def main():
    """Analyze Cosmos DB data"""
    print("🔍 Analyzing Cosmos DB data...")
    
    # Initialize Cosmos client
    cosmos_client = CosmosDBClient()
    
    try:
        # Get sample of documents
        all_matches = list(cosmos_client.container.query_items(
            query="SELECT * FROM c OFFSET 0 LIMIT 10",
            enable_cross_partition_query=True
        ))
        
        print(f"📊 Analyzing {len(all_matches)} sample documents...")
        
        # Analyze data completeness
        stats = {
            'total': len(all_matches),
            'has_odds': 0,
            'has_score': 0,
            'has_league': 0,
            'live_matches': 0,
            'upcoming_matches': 0,
            'odds_examples': [],
            'score_examples': [],
            'league_examples': []
        }
        
        for match in all_matches:
            # Count completeness
            if match.get('odds'):
                stats['has_odds'] += 1
                if len(stats['odds_examples']) < 3:
                    stats['odds_examples'].append(match['odds'])
            
            if match.get('score'):
                stats['has_score'] += 1 
                if len(stats['score_examples']) < 3:
                    stats['score_examples'].append(match['score'])
                    
            if match.get('league'):
                stats['has_league'] += 1
                if match['league'] not in stats['league_examples']:
                    stats['league_examples'].append(match['league'])
            
            # Count status
            if match.get('status') == 'live':
                stats['live_matches'] += 1
            elif match.get('status') == 'upcoming':
                stats['upcoming_matches'] += 1
        
        # Print analysis
        print(f"\n📈 Data Completeness Analysis:")
        print(f"   Total matches: {stats['total']}")
        print(f"   Live matches: {stats['live_matches']}")
        print(f"   Upcoming matches: {stats['upcoming_matches']}")
        print(f"   Have odds: {stats['has_odds']}/{stats['total']} ({stats['has_odds']/stats['total']*100:.1f}%)")
        print(f"   Have scores: {stats['has_score']}/{stats['total']} ({stats['has_score']/stats['total']*100:.1f}%)")
        print(f"   Have league: {stats['has_league']}/{stats['total']} ({stats['has_league']/stats['total']*100:.1f}%)")
        
        if stats['odds_examples']:
            print(f"\n💰 Sample odds data:")
            for i, odds in enumerate(stats['odds_examples']):
                print(f"   Example {i+1}: {odds}")
        else:
            print(f"\n💰 No odds data found!")
            
        if stats['league_examples']:
            print(f"\n🏆 Leagues found: {stats['league_examples']}")
        else:
            print(f"\n🏆 No league data found!")
    
    except Exception as e:
        print(f"❌ Error analyzing data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()