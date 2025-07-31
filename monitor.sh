#!/bin/bash
# Comprehensive monitoring script for HardRock Scraper

RESOURCE_GROUP="pingpong-betting-rg"
CONTAINER_APP_NAME="hr-pong-scraper"

echo "🔍 HardRock Scraper Monitoring Dashboard"
echo "========================================"
echo ""

# 1. Container App Status
echo "📱 Container App Status:"
echo "------------------------"
az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "{
        provisioningState: properties.provisioningState,
        activeRevisions: properties.template.revisions,
        replicas: properties.template.scale,
        currentImage: properties.template.containers[0].image
    }" \
    --output table

echo ""

# 2. Recent Logs
echo "📋 Recent Logs (Last 20 entries):"
echo "----------------------------------"
az containerapp logs show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --tail 20 \
    --query "[].{Time: TimeStamp, Message: Log}" \
    --output table

echo ""

# 3. Health Check (if container is running)
echo "❤️  Health Check:"
echo "-----------------"
APP_FQDN=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv)

if [ ! -z "$APP_FQDN" ]; then
    echo "Health endpoint: https://$APP_FQDN/health"
    
    # Try to fetch health status
    if command -v curl &> /dev/null; then
        echo "Health status:"
        curl -s "https://$APP_FQDN/health" | python3 -m json.tool 2>/dev/null || echo "Health endpoint not responding"
    else
        echo "curl not available - visit https://$APP_FQDN/health manually"
    fi
else
    echo "No external URL configured"
fi

echo ""

# 4. Cosmos DB Quick Check
echo "💾 Cosmos DB Status:"
echo "-------------------"
echo "Database: pingpong_betting"
echo "Container: hardrock_matches"
echo "Note: Use Azure portal or Cosmos client to check data"

echo ""

# 5. GitHub Actions Status
echo "🔄 GitHub Actions:"
echo "------------------"
echo "Latest workflows: https://github.com/jonbondamon/hr-pong-scraper/actions"

echo ""

# 6. Useful Commands
echo "🛠️  Useful Commands:"
echo "--------------------"
echo "View live logs: az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo "Restart app: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --image ghcr.io/jonbondamon/hr-pong-scraper:latest"
echo "Scale to 0: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0"
echo "Scale to 1: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 1"