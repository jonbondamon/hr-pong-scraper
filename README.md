# HardRock Multi-League Table Tennis Scraper

A Python library and containerized application for scraping table tennis betting data from multiple HardRock sportsbook leagues simultaneously and storing it in Azure Cosmos DB.

## Features

- **Multi-League Support**: Scrapes 4 HardRock table tennis leagues simultaneously:
  - Czech Liga Pro
  - TT Cup  
  - TT Elite Series
  - TT Star Series
- **Smart Refresh Strategy**: Minimizes requests by intelligently refreshing live vs upcoming matches
- **Undetectable Chrome**: Uses undetected-chromedriver to avoid detection
- **Azure Cosmos DB Integration**: Direct storage with complete historical tracking of scores, odds, and status changes
- **Container Ready**: Deployed on Azure Container Instances
- **Periodic Scraping**: Configurable intervals (default: 5 minutes) with automatic error recovery

## Quick Start

### 1. Local Development

```bash
# Clone and setup
git clone <repository>
cd hr-pong-scraper

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Basic Usage

```python
from hardrock_scraper import HardRockScraper
from hardrock_scraper.cosmos_client import CosmosDBClient

# Setup Cosmos DB client
cosmos_client = CosmosDBClient(
    endpoint="your-cosmos-endpoint",
    key="your-cosmos-key"
)

# Create scraper with auto-storage
scraper = HardRockScraper(
    base_url="https://sportsbook.hardrocknj.com/en-us/betting/table-tennis",
    cosmos_client=cosmos_client,
    auto_store=True
)

# Get matches once
matches = scraper.get_matches()
print(f"Found {len(matches)} matches")

# Or start continuous monitoring
def callback(matches):
    print(f"Updated: {len(matches)} matches")

scraper.start_monitoring(callback=callback, max_duration=3600)  # 1 hour
```

### 3. Azure Deployment

```bash
# Setup Cosmos DB
cd deployment
./setup-cosmos.sh

# Add Cosmos credentials to .env file
# Then deploy container
./deploy.sh
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chrome        │    │   HardRock       │    │   Azure         │
│   WebDriver     │───▶│   Parser         │───▶│   Cosmos DB     │
│   (Undetected)  │    │   (BeautifulSoup)│    │   (JSON Docs)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
    Smart Refresh            Data Models              Auto-Cleanup
    (10-15s live)         (Match, Player, Odds)      (7 days retention)
```

## Configuration

Environment variables (see `.env.example`):

- `HARDROCK_URL`: Target sportsbook URL
- `COSMOS_ENDPOINT`: Azure Cosmos DB endpoint
- `COSMOS_KEY`: Azure Cosmos DB primary key
- `HEADLESS`: Run Chrome in headless mode (true/false)
- `LIVE_REFRESH_INTERVAL`: Seconds between live match updates (default: 15)
- `UPCOMING_REFRESH_INTERVAL`: Seconds between upcoming match updates (default: 180)
- `MAX_RUNTIME_HOURS`: Maximum container runtime (default: 24)

## Data Models

### Match with Historical Tracking
```json
{
  "match_id": "unique-identifier",
  "player1": {"name": "Player A", "ranking": 15},
  "player2": {"name": "Player B", "ranking": 32},
  "status": "live",
  "score": {
    "current_set": 3,
    "set_scores": ["11-9", "8-11", "5-3"]
  },
  "odds": {
    "player1_moneyline": null,
    "player2_moneyline": "+150"
  },
  "league": "TT Elite Series",
  "created_at": "2025-07-31T12:00:00Z",
  "last_updated": "2025-07-31T12:45:00Z",
  
  "score_history": [
    {"timestamp": "2025-07-31T12:00:00Z", "current_set": 1, "set_scores": ["3-2"]},
    {"timestamp": "2025-07-31T12:15:00Z", "current_set": 1, "set_scores": ["11-9"]},
    {"timestamp": "2025-07-31T12:30:00Z", "current_set": 2, "set_scores": ["11-9", "2-5"]},
    {"timestamp": "2025-07-31T12:45:00Z", "current_set": 3, "set_scores": ["11-9", "8-11", "5-3"]}
  ],
  
  "odds_history": [
    {"timestamp": "2025-07-31T12:00:00Z", "player2_moneyline": "+200"},
    {"timestamp": "2025-07-31T12:25:00Z", "player2_moneyline": "+175"},
    {"timestamp": "2025-07-31T12:45:00Z", "player2_moneyline": "+150"}
  ],
  
  "status_history": [
    {"timestamp": "2025-07-31T11:55:00Z", "status": "upcoming"},
    {"timestamp": "2025-07-31T12:00:00Z", "status": "live"}
  ]
}
```

## Deployment Commands

```bash
# View container logs
az container logs --resource-group pingpong-betting-rg --name hardrock-scraper

# Restart container
az container restart --resource-group pingpong-betting-rg --name hardrock-scraper

# Check container status
az container show --resource-group pingpong-betting-rg --name hardrock-scraper \
  --query containers[0].instanceView.currentState

# Delete container
az container delete --resource-group pingpong-betting-rg --name hardrock-scraper --yes
```

## Cost Optimization

- **Minimum Cosmos DB throughput**: 400 RU/s (~$24/month)
- **Container Instance**: 1 CPU, 2GB RAM (~$35/month)
- **Smart refresh strategy**: <50 full page loads per day
- **Auto-cleanup**: Removes data older than 7 days

**Total estimated cost**: ~$60/month

## Monitoring

The scraper includes built-in logging and monitoring:

- JSON-structured logs
- Container health checks
- Cosmos DB statistics
- Automatic error recovery
- Graceful shutdowns

## License

MIT License