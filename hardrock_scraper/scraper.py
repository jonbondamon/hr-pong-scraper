"""Main HardRock table tennis scraper with smart refresh capabilities"""

import time
import logging
from typing import List, Optional, Dict, Callable
from datetime import datetime, timedelta
from threading import Thread, Event

from .chrome_manager import ChromeManager
from .parser import HardRockParser
from .models import Match, MatchStatus
from .exceptions import ScraperError, ChromeError, ParseError
from .cosmos_client import CosmosDBClient


class HardRockScraper:
    """Main scraper class for HardRock table tennis data"""
    
    def __init__(self, 
                 base_url: str,
                 headless: bool = True,
                 live_refresh_interval: int = 15,
                 upcoming_refresh_interval: int = 180,
                 full_refresh_timeout: int = 300,
                 cosmos_client: Optional[CosmosDBClient] = None,
                 auto_store: bool = False):
        """
        Initialize scraper
        
        Args:
            base_url: HardRock table tennis page URL
            headless: Run Chrome in headless mode
            live_refresh_interval: Seconds between DOM re-parsing for live matches
            upcoming_refresh_interval: Seconds between DOM re-parsing for upcoming matches
            full_refresh_timeout: Seconds before forcing full page refresh
            cosmos_client: Optional Cosmos DB client for data storage
            auto_store: Automatically store matches to Cosmos DB when found
        """
        self.base_url = base_url
        self.headless = headless
        self.live_refresh_interval = live_refresh_interval
        self.upcoming_refresh_interval = upcoming_refresh_interval
        self.full_refresh_timeout = full_refresh_timeout
        
        self.chrome_manager = ChromeManager(headless=headless)
        self.parser = HardRockParser()
        self.cosmos_client = cosmos_client
        self.auto_store = auto_store
        self.logger = logging.getLogger(__name__)
        
        # State management
        self.last_matches: List[Match] = []
        self.last_full_refresh = datetime.now()
        self.last_html = ""
        self.is_monitoring = False
        self.stop_event = Event()
        
    def get_matches(self) -> List[Match]:
        """Get current matches with single page load"""
        try:
            # Start Chrome if not already running
            if not self.chrome_manager.driver:
                self.chrome_manager.start_driver()
            
            # Get page content
            html_content = self.chrome_manager.get_page(self.base_url)
            self.last_html = html_content
            self.last_full_refresh = datetime.now()
            
            # Parse matches
            matches = self.parser.parse_html(html_content)
            self.last_matches = matches
            
            # Auto-store to Cosmos DB if enabled
            if self.auto_store and self.cosmos_client and matches:
                stored_count = self.cosmos_client.store_matches(matches)
                self.logger.info(f"Stored {stored_count} matches to Cosmos DB")
            
            self.logger.info(f"Found {len(matches)} matches")
            return matches
            
        except Exception as e:
            raise ScraperError(f"Failed to get matches: {e}")
    
    def start_monitoring(self, 
                        callback: Optional[Callable[[List[Match]], None]] = None,
                        max_duration: Optional[int] = None) -> Thread:
        """
        Start continuous monitoring with smart refresh
        
        Args:
            callback: Function to call with updated matches
            max_duration: Maximum monitoring duration in seconds
            
        Returns:
            Thread object for the monitoring process
        """
        if self.is_monitoring:
            raise ScraperError("Monitoring already active")
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        def monitor():
            try:
                self._monitor_loop(callback, max_duration)
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
            finally:
                self.is_monitoring = False
        
        thread = Thread(target=monitor, daemon=True)
        thread.start()
        return thread
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.stop_event.set()
        self.is_monitoring = False
    
    def _monitor_loop(self, 
                     callback: Optional[Callable[[List[Match]], None]],
                     max_duration: Optional[int]):
        """Main monitoring loop with smart refresh logic"""
        start_time = datetime.now()
        
        # Initial load
        try:
            matches = self.get_matches()
            if callback:
                callback(matches)
        except Exception as e:
            self.logger.error(f"Initial load failed: {e}")
            return
        
        while not self.stop_event.is_set():
            try:
                # Check if we should stop based on max duration
                if max_duration and (datetime.now() - start_time).seconds > max_duration:
                    break
                
                # Determine refresh strategy
                refresh_interval = self._get_refresh_interval()
                needs_full_refresh = self._needs_full_refresh()
                
                if needs_full_refresh:
                    matches = self._do_full_refresh()
                else:
                    matches = self._do_smart_refresh()
                
                # Update state and call callback
                if matches:
                    self.last_matches = matches
                    if callback:
                        callback(matches)
                
                # Wait for next refresh
                self.stop_event.wait(refresh_interval)
                
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                # Try to recover by doing full refresh
                try:
                    time.sleep(5)  # Brief pause before retry
                    matches = self._do_full_refresh()
                    if matches and callback:
                        callback(matches)
                except:
                    self.logger.error("Recovery failed, continuing...")
                
                self.stop_event.wait(30)  # Wait longer after error
    
    def _get_refresh_interval(self) -> int:
        """Determine appropriate refresh interval based on match states"""
        if not self.last_matches:
            return self.upcoming_refresh_interval
        
        # If any live matches, use live interval
        has_live = any(match.is_live() for match in self.last_matches)
        if has_live:
            return self.live_refresh_interval
        
        return self.upcoming_refresh_interval
    
    def _needs_full_refresh(self) -> bool:
        """Determine if full page refresh is needed"""
        # Time-based refresh
        time_since_refresh = datetime.now() - self.last_full_refresh
        if time_since_refresh.seconds > self.full_refresh_timeout:
            return True
        
        # Chrome health check
        if not self.chrome_manager.is_alive():
            return True
        
        return False
    
    def _do_full_refresh(self) -> List[Match]:
        """Perform full page refresh and parse"""
        self.logger.info("Performing full page refresh")
        
        try:
            # Restart Chrome if needed
            if not self.chrome_manager.is_alive():
                self.chrome_manager.restart_driver()
            
            # Get fresh page content
            html_content = self.chrome_manager.get_page(self.base_url)
            self.last_html = html_content
            self.last_full_refresh = datetime.now()
            
            # Parse matches
            matches = self.parser.parse_html(html_content)
            self.logger.info(f"Full refresh found {len(matches)} matches")
            return matches
            
        except Exception as e:
            self.logger.error(f"Full refresh failed: {e}")
            raise
    
    def _do_smart_refresh(self) -> List[Match]:
        """Try to refresh data without full page reload"""
        try:
            # Try to get updated content via JavaScript refresh
            self.chrome_manager.execute_script("location.reload(true);")
            time.sleep(2)  # Wait for refresh
            
            html_content = self.chrome_manager.driver.page_source
            
            # Only update if content actually changed
            if html_content != self.last_html:
                self.last_html = html_content
                matches = self.parser.parse_html(html_content)
                self.logger.debug(f"Smart refresh found {len(matches)} matches")
                return matches
            
            # No changes, return existing matches
            return self.last_matches
            
        except Exception as e:
            self.logger.warning(f"Smart refresh failed, falling back to full refresh: {e}")
            return self._do_full_refresh()
    
    def get_live_matches(self) -> List[Match]:
        """Get only live matches"""
        matches = self.get_matches() if not self.last_matches else self.last_matches
        return [match for match in matches if match.is_live()]
    
    def get_upcoming_matches(self) -> List[Match]:
        """Get only upcoming matches"""
        matches = self.get_matches() if not self.last_matches else self.last_matches
        return [match for match in matches if match.is_upcoming()]
    
    def get_match_by_players(self, player1: str, player2: str) -> Optional[Match]:
        """Find match by player names"""
        matches = self.last_matches or self.get_matches()
        
        for match in matches:
            if (match.player1.name.lower() == player1.lower() and 
                match.player2.name.lower() == player2.lower()) or \
               (match.player1.name.lower() == player2.lower() and 
                match.player2.name.lower() == player1.lower()):
                return match
        
        return None
    
    def store_matches_to_cosmos(self, matches: Optional[List[Match]] = None) -> int:
        """Store matches to Cosmos DB"""
        if not self.cosmos_client:
            raise ScraperError("Cosmos DB client not configured")
        
        matches_to_store = matches or self.last_matches
        if not matches_to_store:
            self.logger.warning("No matches to store")
            return 0
        
        return self.cosmos_client.store_matches(matches_to_store)
    
    def get_cosmos_stats(self) -> Dict:
        """Get Cosmos DB container statistics"""
        if not self.cosmos_client:
            raise ScraperError("Cosmos DB client not configured")
        
        return self.cosmos_client.get_container_stats()
    
    def close(self):
        """Clean up resources"""
        self.stop_monitoring()
        self.chrome_manager.quit_driver()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()