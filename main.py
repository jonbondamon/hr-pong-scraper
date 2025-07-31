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
    
    # Run periodic scraping
    try:
        logger.info("Starting periodic multi-league scraping...")
        
        start_time = datetime.now()
        last_cleanup = datetime.now()
        
        while True:
            loop_start = datetime.now()
            
            try:
                # Scrape all leagues
                logger.info("Starting scrape cycle...")
                results = multi_scraper.scrape_all_leagues()
                
                # Log summary
                stats = multi_scraper.get_summary_stats()
                logger.info(f"Scrape complete: {stats['total_matches']} total matches, "
                           f"{stats['live_matches']} live, {stats['upcoming_matches']} upcoming")
                
                # Log live matches
                live_matches = [m for m in multi_scraper.all_matches if m.is_live()]
                for match in live_matches:
                    score_str = f" - {match.score}" if match.score else ""
                    odds_str = f" [{match.odds.player1_moneyline}|{match.odds.player2_moneyline}]" if match.odds else ""
                    logger.info(f"LIVE [{match.league}]: {match.player1.name} vs {match.player2.name}{score_str}{odds_str}")
                
                # Update health status
                health_status.update_scrape(success=True)
                
            except Exception as e:
                logger.error(f"Scrape cycle failed: {e}")
                health_status.update_scrape(success=False, error=e)
            
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
            
            # Wait for next scrape cycle
            logger.info(f"Waiting {SCRAPE_INTERVAL_MINUTES} minutes until next scrape...")
            time.sleep(SCRAPE_INTERVAL_MINUTES * 60)
        
        # Final stats
        if cosmos_client:
            final_stats = cosmos_client.get_container_stats()
            logger.info(f"Final Cosmos DB stats: {final_stats}")
        
        multi_scraper.close_all()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        multi_scraper.close_all()
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        multi_scraper.close_all()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)