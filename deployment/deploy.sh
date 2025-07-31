#!/bin/bash

# Azure Container Instance deployment script for HardRock scraper

set -e

# Configuration
RESOURCE_GROUP="pingpong-betting-rg"
CONTAINER_NAME="hardrock-scraper"
IMAGE_NAME="hardrock-scraper"
REGISTRY_NAME="pingpongregistry"
LOCATION="eastus"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏓 HardRock Table Tennis Scraper Deployment${NC}"
echo "=================================================="

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

# Get current subscription
SUBSCRIPTION=$(az account show --query id -o tsv)
echo -e "${GREEN}📋 Using subscription: ${SUBSCRIPTION}${NC}"

# Create resource group if it doesn't exist
echo -e "${YELLOW}📦 Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

# Create container registry if it doesn't exist
echo -e "${YELLOW}🏗️  Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME \
    --sku Basic \
    --admin-enabled true \
    --output none || true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --query loginServer -o tsv)
echo -e "${GREEN}🔗 ACR Login Server: ${ACR_LOGIN_SERVER}${NC}"

# Build and push Docker image
echo -e "${YELLOW}🐳 Building Docker image...${NC}"
cd ..  # Go back to project root
docker build -t $IMAGE_NAME .

echo -e "${YELLOW}🏷️  Tagging image for ACR...${NC}"
docker tag $IMAGE_NAME $ACR_LOGIN_SERVER/$IMAGE_NAME:latest

echo -e "${YELLOW}🔐 Logging into ACR...${NC}"
az acr login --name $REGISTRY_NAME

echo -e "${YELLOW}⬆️  Pushing image to ACR...${NC}"
docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:latest

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --query passwords[0].value -o tsv)

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}❌ .env file not found. Please create one based on .env.example${NC}"
    exit 1
fi

# Load environment variables
source ../.env

# Validate required environment variables
if [ -z "$COSMOS_ENDPOINT" ] || [ -z "$COSMOS_KEY" ]; then
    echo -e "${RED}❌ COSMOS_ENDPOINT and COSMOS_KEY must be set in .env file${NC}"
    exit 1
fi

# Deploy container instance
echo -e "${YELLOW}🚀 Deploying container instance...${NC}"
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_LOGIN_SERVER/$IMAGE_NAME:latest \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --cpu 1 \
    --memory 2 \
    --restart-policy Always \
    --environment-variables \
        HARDROCK_URL="$HARDROCK_URL" \
        HEADLESS="$HEADLESS" \
        LIVE_REFRESH_INTERVAL="$LIVE_REFRESH_INTERVAL" \
        UPCOMING_REFRESH_INTERVAL="$UPCOMING_REFRESH_INTERVAL" \
        FULL_REFRESH_TIMEOUT="$FULL_REFRESH_TIMEOUT" \
        MAX_RUNTIME_HOURS="$MAX_RUNTIME_HOURS" \
        CLEANUP_INTERVAL_HOURS="$CLEANUP_INTERVAL_HOURS" \
        COSMOS_ENDPOINT="$COSMOS_ENDPOINT" \
        COSMOS_KEY="$COSMOS_KEY" \
    --output none

# Get container status
echo -e "${YELLOW}📊 Getting container status...${NC}"
az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query "{Name:name,State:containers[0].instanceView.currentState.state,StartTime:containers[0].instanceView.currentState.startTime}" \
    --output table

echo -e "${GREEN}✅ Deployment completed!${NC}"
echo ""
echo "📝 Useful commands:"
echo "  View logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "  Restart:   az container restart --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "  Delete:    az container delete --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --yes"
echo "  Status:    az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query containers[0].instanceView.currentState"