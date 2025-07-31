# Azure Container Apps Deployment Guide

This guide walks you through deploying the HardRock Multi-League Scraper to Azure Container Apps with GitHub Actions CI/CD.

## 🚀 Quick Deploy

### 1. Prerequisites

- Azure CLI installed and logged in
- GitHub account with repository access
- Azure subscription with Container Apps enabled

### 2. One-Time Setup

```bash
# Clone repository
git clone https://github.com/jonbondamon/hr-pong-scraper.git
cd hr-pong-scraper

# Deploy to Azure
./deployment/deploy-containerapp.sh
```

## 🔧 Manual Setup

### 1. Azure Resources

```bash
# Set variables
RESOURCE_GROUP="pingpong-betting-rg"
CONTAINER_APP_NAME="hr-pong-scraper"
CONTAINER_ENVIRONMENT="pingpong-betting-env"
LOCATION="eastus"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Container Apps environment
az containerapp env create \
    --name $CONTAINER_ENVIRONMENT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
```

### 2. Deploy Container App

```bash
# Deploy the application
az containerapp create \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENVIRONMENT \
    --image ghcr.io/jonbondamon/hr-pong-scraper:latest \
    --cpu 1.0 \
    --memory 2Gi \
    --min-replicas 1 \
    --max-replicas 1 \
    --env-vars \
        HEADLESS=true \
        MAX_RUNTIME_HOURS=12 \
        SCRAPE_INTERVAL_MINUTES=3 \
        LIVE_REFRESH_INTERVAL=5 \
    --secrets \
        cosmos-endpoint="YOUR_COSMOS_ENDPOINT" \
        cosmos-key="YOUR_COSMOS_KEY" \
    --env-vars \
        COSMOS_ENDPOINT=secretref:cosmos-endpoint \
        COSMOS_KEY=secretref:cosmos-key
```

## 🔄 CI/CD Pipeline Setup

### 1. GitHub Secrets

Add these secrets to your GitHub repository:

```
AZURE_CREDENTIALS - Azure service principal JSON
```

Create service principal:
```bash
az ad sp create-for-rbac \
    --name "hr-pong-scraper-deploy" \
    --role contributor \
    --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/pingpong-betting-rg \
    --sdk-auth
```

### 2. Automatic Deployment

The pipeline automatically:
- ✅ Runs tests on push/PR
- 🐳 Builds and pushes Docker image to GHCR
- 🚀 Deploys to Azure Container Apps on main branch

## 📊 Monitoring & Management

### View Logs
```bash
az containerapp logs show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --follow
```

### Health Check
```bash
# Get app URL
APP_FQDN=$(az containerapp show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv)

# Check health
curl https://$APP_FQDN/health
```

### Update Configuration
```bash
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --set-env-vars SCRAPE_INTERVAL_MINUTES=2
```

### Scale Application
```bash
# Scale to 0 (pause)
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --min-replicas 0 \
    --max-replicas 0

# Scale back up
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --min-replicas 1 \
    --max-replicas 1
```

## 💰 Cost Management

### Current Configuration
- **Container**: 1 CPU, 2GB RAM = ~$35/month
- **Cosmos DB**: 400 RU/s = ~$24/month
- **Total**: ~$59/month

### Cost Optimization
```bash
# Reduce to 0.5 CPU, 1GB RAM
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --cpu 0.5 \
    --memory 1Gi

# Schedule scaling (requires Logic Apps)
# Scale down during low-activity hours
```

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS` | `true` | Run Chrome in headless mode |
| `MAX_RUNTIME_HOURS` | `12` | Container restart interval |
| `SCRAPE_INTERVAL_MINUTES` | `3` | Time between scrape cycles |
| `LIVE_REFRESH_INTERVAL` | `5` | Seconds between live match updates |
| `COSMOS_ENDPOINT` | - | Cosmos DB endpoint (secret) |
| `COSMOS_KEY` | - | Cosmos DB key (secret) |
| `COSMOS_DATABASE_NAME` | `pingpong-betting` | Database name |
| `COSMOS_CONTAINER_NAME` | `hardrock_matches` | Container name |

## 🛠️ Troubleshooting

### Common Issues

**Container not starting:**
```bash
# Check events
az containerapp show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --query "properties.template.containers[0].probes"
```

**Memory issues:**
```bash
# Increase memory
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --memory 4Gi
```

**Chrome crashes:**
```bash
# Check logs for Chrome errors
az containerapp logs show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --container hr-pong-scraper
```

### Debug Commands
```bash
# Container status
az containerapp show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --query "properties.provisioningState"

# Resource usage
az containerapp show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --query "properties.template.containers[0].resources"

# Environment variables
az containerapp show \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --query "properties.template.containers[0].env"
```

## 🔄 Updates & Maintenance

### Manual Update
```bash
# Update to latest image
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --image ghcr.io/jonbondamon/hr-pong-scraper:latest
```

### Rollback
```bash
# Rollback to previous version
az containerapp update \
    --name hr-pong-scraper \
    --resource-group pingpong-betting-rg \
    --image ghcr.io/jonbondamon/hr-pong-scraper:v1.0.0
```

## 🚨 Cleanup

```bash
# Delete everything
az group delete --name pingpong-betting-rg --yes --no-wait
```