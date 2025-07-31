"""Azure Cosmos DB client for storing HardRock betting data"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosHttpResponseError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .models import Match


class CosmosDBClient:
    """Client for interacting with Azure Cosmos DB"""
    
    def __init__(self, 
                 endpoint: Optional[str] = None,
                 key: Optional[str] = None,
                 database_name: Optional[str] = None,
                 container_name: Optional[str] = None):
        """
        Initialize Cosmos DB client
        
        Args:
            endpoint: Cosmos DB endpoint URL
            key: Cosmos DB primary key
            database_name: Database name
            container_name: Container name for matches
        """
        self.endpoint = endpoint or os.getenv("COSMOS_ENDPOINT")
        self.key = key or os.getenv("COSMOS_KEY")
        self.database_name = database_name or os.getenv("COSMOS_DATABASE_NAME", "pingpong_betting")
        self.container_name = container_name or os.getenv("COSMOS_CONTAINER_NAME", "hardrock_matches")
        
        if not self.endpoint or not self.key:
            raise ValueError("Cosmos DB endpoint and key must be provided via parameters or environment variables")
        
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = None
        self.container = None
        self.logger = logging.getLogger(__name__)
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and container"""
        try:
            # Create database if it doesn't exist
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create container if it doesn't exist
            self.container = self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/match_id"),
                offer_throughput=400  # Minimum throughput for cost optimization
            )
            
            self.logger.info(f"Initialized Cosmos DB: {self.database_name}/{self.container_name}")
            
        except CosmosHttpResponseError as e:
            self.logger.error(f"Failed to initialize Cosmos DB: {e}")
            raise
    
    def store_matches(self, matches: List[Match]) -> int:
        """
        Store matches in Cosmos DB with historical tracking
        
        Args:
            matches: List of Match objects to store
            
        Returns:
            Number of matches successfully stored
        """
        stored_count = 0
        
        for match in matches:
            try:
                # Get existing document if it exists
                existing_doc = self.get_match(match.match_id)
                
                if existing_doc:
                    # Update existing document with new data
                    updated_doc = self._update_match_with_history(existing_doc, match)
                else:
                    # Create new document
                    updated_doc = self._match_to_document(match)
                
                # Upsert the document
                self.container.upsert_item(updated_doc)
                stored_count += 1
                
            except CosmosHttpResponseError as e:
                self.logger.error(f"Failed to store match {match.match_id}: {e}")
                continue
        
        self.logger.info(f"Stored {stored_count}/{len(matches)} matches")
        return stored_count
    
    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID"""
        try:
            return self.container.read_item(
                item=match_id,
                partition_key=match_id
            )
        except CosmosHttpResponseError:
            return None
    
    def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches"""
        query = "SELECT * FROM c WHERE c.status = 'live'"
        return list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Get all upcoming matches"""
        query = "SELECT * FROM c WHERE c.status = 'upcoming'"
        return list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    def get_recent_matches(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get matches from the last N hours"""
        query = f"""
        SELECT * FROM c 
        WHERE c.last_updated >= DateTimeAdd('hour', -{hours}, GetCurrentDateTime())
        ORDER BY c.last_updated DESC
        """
        return list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    def delete_old_matches(self, days: int = 7) -> int:
        """Delete matches older than N days"""
        query = f"""
        SELECT c.id, c.match_id FROM c 
        WHERE c.last_updated <= DateTimeAdd('day', -{days}, GetCurrentDateTime())
        """
        
        items_to_delete = list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        deleted_count = 0
        for item in items_to_delete:
            try:
                self.container.delete_item(
                    item=item['id'],
                    partition_key=item['match_id']
                )
                deleted_count += 1
            except CosmosHttpResponseError as e:
                self.logger.error(f"Failed to delete match {item['id']}: {e}")
        
        self.logger.info(f"Deleted {deleted_count} old matches")
        return deleted_count
    
    def get_match_history(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get full match history including score/odds changes"""
        return self.get_match(match_id)
    
    def get_odds_changes(self, match_id: str) -> List[Dict[str, Any]]:
        """Get odds change history for a specific match"""
        match_doc = self.get_match(match_id)
        if match_doc and 'odds_history' in match_doc:
            return match_doc['odds_history']
        return []
    
    def get_score_progression(self, match_id: str) -> List[Dict[str, Any]]:
        """Get score progression for a specific match"""
        match_doc = self.get_match(match_id)
        if match_doc and 'score_history' in match_doc:
            return match_doc['score_history']
        return []
    
    def get_matches_with_odds_changes(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get matches that had odds changes in the last N hours"""
        query = f"""
        SELECT c.id, c.match_id, c.player1, c.player2, c.league, 
               ARRAY_LENGTH(c.odds_history) as odds_changes,
               c.odds_history[ARRAY_LENGTH(c.odds_history)-1] as latest_odds,
               c.odds_history[0] as initial_odds
        FROM c 
        WHERE c.last_updated >= DateTimeAdd('hour', -{hours}, GetCurrentDateTime())
        AND ARRAY_LENGTH(c.odds_history) > 1
        ORDER BY c.last_updated DESC
        """
        return list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    def get_live_score_changes(self, hours: int = 2) -> List[Dict[str, Any]]:
        """Get live matches with recent score changes"""
        query = f"""
        SELECT c.id, c.match_id, c.player1, c.player2, c.league,
               ARRAY_LENGTH(c.score_history) as score_updates,
               c.score_history[ARRAY_LENGTH(c.score_history)-1] as current_score
        FROM c 
        WHERE c.status = 'live'
        AND c.last_updated >= DateTimeAdd('hour', -{hours}, GetCurrentDateTime())
        AND ARRAY_LENGTH(c.score_history) > 0
        ORDER BY c.last_updated DESC
        """
        return list(self.container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    def _match_to_document(self, match: Match) -> Dict[str, Any]:
        """Convert Match object to Cosmos DB document with historical tracking"""
        doc = match.to_dict()
        current_time = datetime.now().isoformat()
        
        # Add Cosmos DB specific fields
        doc['id'] = match.match_id  # Required by Cosmos DB
        doc['created_at'] = current_time
        doc['last_updated'] = current_time
        doc['scrape_source'] = 'hardrock'
        
        # Ensure partition key is set
        doc['match_id'] = match.match_id
        
        # Initialize historical tracking arrays
        doc['score_history'] = []
        doc['odds_history'] = []
        doc['status_history'] = []
        
        # Add initial entries to history
        if match.score:
            doc['score_history'].append({
                'timestamp': current_time,
                'current_set': match.score.current_set,
                'set_scores': match.score.set_scores,
                'total_games': match.score.total_games
            })
        
        if match.odds:
            doc['odds_history'].append({
                'timestamp': current_time,
                'player1_moneyline': match.odds.player1_moneyline,
                'player2_moneyline': match.odds.player2_moneyline,
                'handicap_line': match.odds.handicap_line,
                'player1_handicap': match.odds.player1_handicap,
                'player2_handicap': match.odds.player2_handicap,
                'over_under_line': match.odds.over_under_line,
                'over_odds': match.odds.over_odds,
                'under_odds': match.odds.under_odds
            })
        
        doc['status_history'].append({
            'timestamp': current_time,
            'status': match.status.value
        })
        
        return doc
    
    def _update_match_with_history(self, existing_doc: Dict[str, Any], new_match: Match) -> Dict[str, Any]:
        """Update existing document with new match data, preserving history"""
        current_time = datetime.now().isoformat()
        
        # Update basic match info
        new_doc = new_match.to_dict()
        
        # Preserve Cosmos DB fields and history
        new_doc['id'] = existing_doc['id']
        new_doc['match_id'] = existing_doc['match_id']
        new_doc['created_at'] = existing_doc.get('created_at', current_time)
        new_doc['last_updated'] = current_time
        new_doc['scrape_source'] = existing_doc.get('scrape_source', 'hardrock')
        
        # Initialize history arrays if they don't exist (backward compatibility)
        new_doc['score_history'] = existing_doc.get('score_history', [])
        new_doc['odds_history'] = existing_doc.get('odds_history', [])
        new_doc['status_history'] = existing_doc.get('status_history', [])
        
        # Check if score changed and add to history
        if new_match.score:
            current_score = {
                'current_set': new_match.score.current_set,
                'set_scores': new_match.score.set_scores,
                'total_games': new_match.score.total_games
            }
            
            # Only add if score actually changed
            if not new_doc['score_history'] or self._score_changed(new_doc['score_history'][-1], current_score):
                new_doc['score_history'].append({
                    'timestamp': current_time,
                    **current_score
                })
        
        # Check if odds changed and add to history
        if new_match.odds:
            current_odds = {
                'player1_moneyline': new_match.odds.player1_moneyline,
                'player2_moneyline': new_match.odds.player2_moneyline,
                'handicap_line': new_match.odds.handicap_line,
                'player1_handicap': new_match.odds.player1_handicap,
                'player2_handicap': new_match.odds.player2_handicap,
                'over_under_line': new_match.odds.over_under_line,
                'over_odds': new_match.odds.over_odds,
                'under_odds': new_match.odds.under_odds
            }
            
            # Only add if odds actually changed
            if not new_doc['odds_history'] or self._odds_changed(new_doc['odds_history'][-1], current_odds):
                new_doc['odds_history'].append({
                    'timestamp': current_time,
                    **current_odds
                })
        
        # Check if status changed and add to history
        current_status = new_match.status.value
        if not new_doc['status_history'] or new_doc['status_history'][-1]['status'] != current_status:
            new_doc['status_history'].append({
                'timestamp': current_time,
                'status': current_status
            })
        
        # Limit history size to prevent documents from growing too large
        max_history_entries = 100
        if len(new_doc['score_history']) > max_history_entries:
            new_doc['score_history'] = new_doc['score_history'][-max_history_entries:]
        if len(new_doc['odds_history']) > max_history_entries:
            new_doc['odds_history'] = new_doc['odds_history'][-max_history_entries:]
        if len(new_doc['status_history']) > max_history_entries:
            new_doc['status_history'] = new_doc['status_history'][-max_history_entries:]
        
        return new_doc
    
    def _score_changed(self, old_score: Dict, new_score: Dict) -> bool:
        """Check if score has actually changed"""
        return (old_score.get('current_set') != new_score.get('current_set') or
                old_score.get('set_scores') != new_score.get('set_scores') or
                old_score.get('total_games') != new_score.get('total_games'))
    
    def _odds_changed(self, old_odds: Dict, new_odds: Dict) -> bool:
        """Check if odds have actually changed"""
        return (old_odds.get('player1_moneyline') != new_odds.get('player1_moneyline') or
                old_odds.get('player2_moneyline') != new_odds.get('player2_moneyline') or
                old_odds.get('handicap_line') != new_odds.get('handicap_line') or
                old_odds.get('player1_handicap') != new_odds.get('player1_handicap') or
                old_odds.get('player2_handicap') != new_odds.get('player2_handicap') or
                old_odds.get('over_under_line') != new_odds.get('over_under_line') or
                old_odds.get('over_odds') != new_odds.get('over_odds') or
                old_odds.get('under_odds') != new_odds.get('under_odds'))
    
    def get_container_stats(self) -> Dict[str, Any]:
        """Get container statistics"""
        try:
            # Count total matches
            total_query = "SELECT VALUE COUNT(1) FROM c"
            total_count = list(self.container.query_items(
                query=total_query,
                enable_cross_partition_query=True
            ))[0]
            
            # Count live matches
            live_query = "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'live'"
            live_count = list(self.container.query_items(
                query=live_query,
                enable_cross_partition_query=True
            ))[0]
            
            # Count upcoming matches
            upcoming_query = "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'upcoming'"
            upcoming_count = list(self.container.query_items(
                query=upcoming_query,
                enable_cross_partition_query=True
            ))[0]
            
            return {
                'total_matches': total_count,
                'live_matches': live_count,
                'upcoming_matches': upcoming_count,
                'last_checked': datetime.now().isoformat()
            }
            
        except CosmosHttpResponseError as e:
            self.logger.error(f"Failed to get container stats: {e}")
            return {}