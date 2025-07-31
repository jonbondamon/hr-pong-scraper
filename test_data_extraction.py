#!/usr/bin/env python3
"""Test script to examine what data is being extracted"""

import sys
import json
from pathlib import Path

# Add the hardrock_scraper package to path
sys.path.insert(0, str(Path(__file__).parent))

from hardrock_scraper.cosmos_client import CosmosDBClient

def main():
    """Test what data is in Cosmos DB"""
    print("🔍 Testing Cosmos DB data extraction...")
    
    # Initialize Cosmos client
    cosmos_client = CosmosDBClient()
    
    # Get all matches
    try:
        all_matches = list(cosmos_client.container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        ))
        
        print(f"📊 Found {len(all_matches)} documents in Cosmos DB")
        
        if all_matches:
            # Print first document structure
            first_match = all_matches[0]
            print("\n📋 First document structure:")
            print(json.dumps(first_match, indent=2, default=str))
            
            # Check what fields are present
            print(f"\n🔑 Fields in document: {list(first_match.keys())}")
            
            # Check player data specifically
            if 'player1' in first_match:
                print(f"\n👤 Player 1 data: {first_match['player1']}")
            if 'player2' in first_match:
                print(f"👤 Player 2 data: {first_match['player2']}")
            
            # Check score data
            if 'score' in first_match:
                print(f"\n⚽ Score data: {first_match['score']}")
            
            # Check odds data
            if 'odds' in first_match:
                print(f"\n💰 Odds data: {first_match['odds']}")
            
            # Check status
            if 'status' in first_match:
                print(f"\n📊 Status: {first_match['status']}")
                
        else:
            print("❌ No documents found in Cosmos DB")
    
    except Exception as e:
        print(f"❌ Error querying Cosmos DB: {e}")

if __name__ == "__main__":
    main()