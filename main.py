"""Main application for HardRock table tennis scraper with Cosmos DB integration"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

from hardrock_scraper import HardRockScraper
from hardrock_scraper.cosmos_client import CosmosDBClient
from multi_league_scraper import MultiLeagueScraper
from health_server import start_health_server

# Load environment variables
load_dotenv()

# Configure logging with debug level for parser
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/scraper.log')
    ]
)

# Reduce noise from Azure logs but keep our debug logs
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    
    # Configuration from environment variables
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    COSMOS_KEY = os.getenv("COSMOS_KEY")
    
    # Scraper configuration
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    LIVE_REFRESH_INTERVAL = int(os.getenv("LIVE_REFRESH_INTERVAL", "15"))
    UPCOMING_REFRESH_INTERVAL = int(os.getenv("UPCOMING_REFRESH_INTERVAL", "180"))
    FULL_REFRESH_TIMEOUT = int(os.getenv("FULL_REFRESH_TIMEOUT", "300"))
    
    # Monitoring configuration
    MAX_RUNTIME_HOURS = int(os.getenv("MAX_RUNTIME_HOURS", "24"))
    CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", "6"))
    SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "5"))
    
    logger.info("Starting HardRock Multi-League Table Tennis Scraper")
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info(f"Max runtime: {MAX_RUNTIME_HOURS} hours")
    logger.info(f"Scrape interval: {SCRAPE_INTERVAL_MINUTES} minutes")
    
    # Start health check server
    health_server, health_status = start_health_server(port=8080)
    logger.info("Health check server started on port 8080")
    
    # Initialize Cosmos DB client
    cosmos_client = None
    if COSMOS_ENDPOINT and COSMOS_KEY:
        try:
            cosmos_client = CosmosDBClient(
                endpoint=COSMOS_ENDPOINT,
                key=COSMOS_KEY
            )
            logger.info("Cosmos DB client initialized successfully")
            
            # Print initial stats
            stats = cosmos_client.get_container_stats()
            logger.info(f"Initial Cosmos DB stats: {stats}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB client: {e}")
            return 1
    else:
        logger.warning("Cosmos DB credentials not provided - running without storage")
    
    # Initialize multi-league scraper
    try:
        multi_scraper = MultiLeagueScraper(
            cosmos_client=cosmos_client,
            headless=HEADLESS
        )
        
        multi_scraper.initialize_scrapers()
        logger.info("Multi-league scraper initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize multi-league scraper: {e}")
        return 1
    
    # Run continuous monitoring with smart refresh
    try:
        logger.info("Starting continuous multi-league monitoring...")
        
        start_time = datetime.now()
        last_cleanup = datetime.now()
        monitoring_threads = []
        
        def match_callback_with_league(matches, league_name):
            """Callback that adds league info to matches and processes them"""
            try:
                # Add league info to matches
                for match in matches:
                    match.league = league_name
                
                # Store matches to Cosmos DB (auto-storage is handled by scraper)
                # Just log live matches with changes
                live_matches = [m for m in matches if m.is_live()]
                if live_matches:
                    for match in live_matches:
                        score_str = f" - {match.score}" if match.score else ""
                        odds_str = f" [{match.odds.player1_moneyline}|{match.odds.player2_moneyline}]" if match.odds else ""
                        logger.info(f"LIVE [{match.league}]: {match.player1.name} vs {match.player2.name}{score_str}{odds_str}")
                
                # Update health status
                health_status.update_scrape(success=True)
                
            except Exception as e:
                logger.error(f"Match callback error for {league_name}: {e}")
        
        # Start monitoring threads for each league
        for league_name, scraper in multi_scraper.scrapers.items():
            logger.info(f"Starting continuous monitoring for {league_name}")
            
            # Configure scraper with proper intervals and Cosmos client
            scraper.live_refresh_interval = LIVE_REFRESH_INTERVAL
            scraper.upcoming_refresh_interval = UPCOMING_REFRESH_INTERVAL
            scraper.full_refresh_timeout = FULL_REFRESH_TIMEOUT
            scraper.cosmos_client = cosmos_client
            scraper.auto_store = True  # Enable auto-storage
            
            # Create league-specific callback
            league_callback = lambda matches, league=league_name: match_callback_with_league(matches, league)
            
            # Start monitoring thread
            thread = scraper.start_monitoring(
                callback=league_callback,
                max_duration=MAX_RUNTIME_HOURS * 3600
            )
            monitoring_threads.append((league_name, thread))
        
        logger.info(f"Started {len(monitoring_threads)} monitoring threads")
        
        # Main monitoring loop
        while True:
            # Check if all threads are still alive
            active_threads = [(name, thread) for name, thread in monitoring_threads if thread.is_alive()]
            
            if len(active_threads) != len(monitoring_threads):
                dead_threads = [name for name, thread in monitoring_threads if not thread.is_alive()]
                logger.warning(f"Monitoring threads died: {dead_threads}")
                # Could restart dead threads here if needed
            
            # Periodic cleanup
            if cosmos_client and (datetime.now() - last_cleanup).seconds > (CLEANUP_INTERVAL_HOURS * 3600):
                try:
                    deleted_count = cosmos_client.delete_old_matches(days=7)
                    logger.info(f"Cleanup: deleted {deleted_count} old matches")
                    last_cleanup = datetime.now()
                except Exception as e:
                    logger.error(f"Cleanup failed: {e}")
            
            # Check max runtime
            runtime_hours = (datetime.now() - start_time).seconds / 3600
            if runtime_hours >= MAX_RUNTIME_HOURS:
                logger.info(f"Max runtime of {MAX_RUNTIME_HOURS} hours reached")
                break
            
            # Sleep for a short time before checking again
            time.sleep(30)  # Check every 30 seconds
        
        # Stop all monitoring threads
        logger.info("Stopping all monitoring threads...")
        for league_name, scraper in multi_scraper.scrapers.items():
            scraper.stop_monitoring()
        
        # Wait for threads to finish
        for league_name, thread in monitoring_threads:
            if thread.is_alive():
                logger.info(f"Waiting for {league_name} monitoring thread to stop...")
                thread.join(timeout=10)
        
        # Final stats
        if cosmos_client:
            final_stats = cosmos_client.get_container_stats()
            logger.info(f"Final Cosmos DB stats: {final_stats}")
        
        multi_scraper.close_all()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        # Stop all monitoring threads
        for league_name, scraper in multi_scraper.scrapers.items():
            scraper.stop_monitoring()
        multi_scraper.close_all()
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        # Stop all monitoring threads
        for league_name, scraper in multi_scraper.scrapers.items():
            scraper.stop_monitoring()
        multi_scraper.close_all()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)