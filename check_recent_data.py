#!/usr/bin/env python3
"""Check most recent Cosmos DB documents"""

import sys
import json
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper.cosmos_client import CosmosDBClient

def main():
    """Check most recent Cosmos DB documents"""
    print("🔍 Checking most recent Cosmos DB documents...")
    
    # Initialize Cosmos client
    cosmos_client = CosmosDBClient()
    
    try:
        # Get most recent documents
        recent_matches = list(cosmos_client.container.query_items(
            query="SELECT * FROM c ORDER BY c.last_updated DESC OFFSET 0 LIMIT 5",
            enable_cross_partition_query=True
        ))
        
        print(f"📊 Found {len(recent_matches)} recent documents")
        
        for i, match in enumerate(recent_matches):
            print(f"\n📋 Document {i+1}:")
            print(f"   Match ID: {match.get('match_id')}")
            print(f"   Players: {match.get('player1', {}).get('name')} vs {match.get('player2', {}).get('name')}")
            print(f"   Status: {match.get('status')}")
            print(f"   League: {match.get('league')}")
            print(f"   Last Updated: {match.get('last_updated')}")
            print(f"   Created: {match.get('created_at')}")
            
            # Check odds
            odds = match.get('odds')
            if odds:
                print(f"   Odds: {odds.get('player1_moneyline')} | {odds.get('player2_moneyline')}")
            else:
                print(f"   Odds: None")
            
            # Check score
            score = match.get('score')
            if score:
                print(f"   Score: Set {score.get('current_set')}, {score.get('set_scores')}")
            else:
                print(f"   Score: None")
                
            # Check history lengths
            score_history = match.get('score_history', [])
            odds_history = match.get('odds_history', [])
            status_history = match.get('status_history', [])
            
            print(f"   History: {len(score_history)} scores, {len(odds_history)} odds, {len(status_history)} statuses")
    
    except Exception as e:
        print(f"❌ Error querying Cosmos DB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()