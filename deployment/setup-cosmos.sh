#!/bin/bash

# Script to create Azure Cosmos DB for the scraper

set -e

# Configuration
RESOURCE_GROUP="pingpong-betting-rg"
COSMOS_ACCOUNT="pingpong-cosmos"
DATABASE_NAME="pingpong_betting"
CONTAINER_NAME="hardrock_matches"
LOCATION="eastus"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌟 Setting up Azure Cosmos DB${NC}"
echo "================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Please login first.${NC}"
    az login
fi

# Create resource group if it doesn't exist
echo -e "${YELLOW}📦 Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

# Create Cosmos DB account
echo -e "${YELLOW}🌍 Creating Cosmos DB account (this may take a few minutes)...${NC}"
az cosmosdb create \
    --resource-group $RESOURCE_GROUP \
    --name $COSMOS_ACCOUNT \
    --kind GlobalDocumentDB \
    --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=False \
    --default-consistency-level Session \
    --enable-automatic-failover false \
    --enable-multiple-write-locations false \
    --output none

# Create database
echo -e "${YELLOW}🗄️  Creating database...${NC}"
az cosmosdb sql database create \
    --account-name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --name $DATABASE_NAME \
    --output none

# Create container
echo -e "${YELLOW}📊 Creating container...${NC}"
az cosmosdb sql container create \
    --account-name $COSMOS_ACCOUNT \
    --database-name $DATABASE_NAME \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --partition-key-path "/match_id" \
    --throughput 400 \
    --output none

# Get connection details
echo -e "${YELLOW}🔑 Getting connection details...${NC}"
COSMOS_ENDPOINT=$(az cosmosdb show --resource-group $RESOURCE_GROUP --name $COSMOS_ACCOUNT --query documentEndpoint -o tsv)
COSMOS_KEY=$(az cosmosdb keys list --resource-group $RESOURCE_GROUP --name $COSMOS_ACCOUNT --query primaryMasterKey -o tsv)

echo -e "${GREEN}✅ Cosmos DB setup completed!${NC}"
echo ""
echo "📋 Connection Details:"
echo "  Endpoint: $COSMOS_ENDPOINT"
echo "  Primary Key: $COSMOS_KEY"
echo ""
echo "📝 Add these to your .env file:"
echo "COSMOS_ENDPOINT=$COSMOS_ENDPOINT"
echo "COSMOS_KEY=$COSMOS_KEY"
echo ""
echo "🌐 Portal URL:"
echo "https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOS_ACCOUNT"