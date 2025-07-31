#!/bin/bash
# Azure Container App Deployment Script

set -e

# Configuration
RESOURCE_GROUP="pingpong-betting-rg"
CONTAINER_APP_NAME="hr-pong-scraper"
CONTAINER_ENVIRONMENT="pingpong-betting-env"
LOCATION="eastus"
SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID}

echo "🚀 Deploying HardRock Scraper to Azure Container Apps"
echo "=================================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Container App: $CONTAINER_APP_NAME"
echo "Environment: $CONTAINER_ENVIRONMENT"
echo "Location: $LOCATION"
echo ""

# Check if Azure CLI is installed and logged in
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

# Set subscription if provided
if [ ! -z "$SUBSCRIPTION_ID" ]; then
    echo "🔧 Setting subscription to: $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Install Container Apps extension
echo "🔧 Installing Container Apps extension..."
az extension add --name containerapp --upgrade

# Register providers
echo "🔧 Registering required providers..."
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Create resource group if it doesn't exist
echo "📁 Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

# Create Container Apps environment
echo "🌍 Creating Container Apps environment..."
az containerapp env create \
    --name "$CONTAINER_ENVIRONMENT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output table

# Prompt for Cosmos DB credentials if not set
if [ -z "$COSMOS_ENDPOINT" ]; then
    echo ""
    echo "🔑 Cosmos DB Configuration Required"
    echo "Please provide your Cosmos DB credentials:"
    read -p "Cosmos DB Endpoint: " COSMOS_ENDPOINT
    read -s -p "Cosmos DB Key: " COSMOS_KEY
    echo ""
fi

# Create or update the container app
echo "🐳 Deploying container app..."
az containerapp create \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_ENVIRONMENT" \
    --image "ghcr.io/jonbondamon/hr-pong-scraper:latest" \
    --cpu 1.0 \
    --memory 2Gi \
    --min-replicas 1 \
    --max-replicas 1 \
    --env-vars \
        HEADLESS=true \
        LIVE_REFRESH_INTERVAL=5 \
        UPCOMING_REFRESH_INTERVAL=180 \
        FULL_REFRESH_TIMEOUT=300 \
        MAX_RUNTIME_HOURS=12 \
        CLEANUP_INTERVAL_HOURS=6 \
        SCRAPE_INTERVAL_MINUTES=3 \
        COSMOS_DATABASE_NAME=pingpong-betting \
        COSMOS_CONTAINER_NAME=hardrock_matches \
    --secrets \
        cosmos-endpoint="$COSMOS_ENDPOINT" \
        cosmos-key="$COSMOS_KEY" \
    --env-vars \
        COSMOS_ENDPOINT=secretref:cosmos-endpoint \
        COSMOS_KEY=secretref:cosmos-key \
    --output table

# Get the app URL
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Container App Details:"
az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv

echo ""
echo "📋 Useful Commands:"
echo "View logs: az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo "Update app: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --image ghcr.io/jonbondamon/hr-pong-scraper:latest"
echo "Scale app: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 0 --max-replicas 1"
echo "Delete app: az containerapp delete --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --yes"