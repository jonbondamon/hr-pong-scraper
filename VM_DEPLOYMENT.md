# Azure VM Deployment Guide

## Overview
This guide covers deploying the HardRock scraper to an Azure Virtual Machine for better Chrome compatibility and control.

## VM Requirements
- **OS**: Ubuntu 20.04 LTS or 22.04 LTS
- **Size**: Standard_B2s (2 vCPUs, 4 GB RAM) minimum
- **Storage**: 30 GB Premium SSD
- **Network**: Allow inbound SSH (22) and optionally HTTP (80) for monitoring

## Pre-deployment Setup

### 1. Create Azure VM
```bash
# Create resource group
az group create --name hr-scraper-rg --location eastus

# Create VM
az vm create \
  --resource-group hr-scraper-rg \
  --name hr-scraper-vm \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

### 2. VM Initial Setup
```bash
# Connect to VM
ssh azureuser@<VM_PUBLIC_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# Install Chrome dependencies
sudo apt install -y wget curl unzip xvfb
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# Install ChromeDriver
CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d '.' -f1)
wget -N https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION} -q -O /tmp/version
CHROMEDRIVER_VERSION=$(cat /tmp/version)
wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

## Application Deployment

### 1. Deploy Application Code
```bash
# Clone repository
git clone https://github.com/jonbondamon/hr-pong-scraper.git
cd hr-pong-scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Create environment file
cat > .env << EOF
# Cosmos DB Configuration
COSMOS_ENDPOINT=<your-cosmos-endpoint>
COSMOS_KEY=<your-cosmos-key>
COSMOS_DATABASE_NAME=pingpong_betting
COSMOS_CONTAINER_NAME=matches

# Scraper Configuration
SCRAPER_HEADLESS=true
SCRAPER_LIVE_REFRESH_INTERVAL=5
SCRAPER_UPCOMING_REFRESH_INTERVAL=180
MAX_RUNTIME_HOURS=24

# Debug (optional)
SAVE_DEBUG_HTML=false
EOF
```

### 3. Create Systemd Service
```bash
# Create service file
sudo tee /etc/systemd/system/hr-scraper.service << EOF
[Unit]
Description=HardRock Table Tennis Scraper
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/hr-pong-scraper
Environment=PATH=/home/azureuser/hr-pong-scraper/venv/bin
EnvironmentFile=/home/azureuser/hr-pong-scraper/.env
ExecStart=/home/azureuser/hr-pong-scraper/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable hr-scraper
sudo systemctl start hr-scraper
```

## Monitoring and Management

### Check Service Status
```bash
# Service status
sudo systemctl status hr-scraper

# View logs
sudo journalctl -u hr-scraper -f

# Restart service
sudo systemctl restart hr-scraper
```

### Manual Testing
```bash
# Test scraper manually
cd /home/azureuser/hr-pong-scraper
source venv/bin/activate
python main.py
```

## Troubleshooting

### Chrome Issues
- Ensure Chrome is installed: `google-chrome --version`
- Check ChromeDriver: `chromedriver --version`
- Test headless mode: `google-chrome --headless --no-sandbox --dump-dom https://google.com`

### Network Issues
- Check VM network security group allows outbound HTTPS
- Verify Cosmos DB connection: `ping <cosmos-endpoint>`

### Performance Monitoring
```bash
# Monitor resource usage
htop

# Check disk space
df -h

# Monitor network
netstat -tulpn
```

## Scaling and Optimization

### For Higher Load
- Upgrade to Standard_B4ms (4 vCPUs, 16 GB RAM)
- Enable multiple league monitoring threads
- Implement load balancing with multiple VMs

### Cost Optimization
- Use B-series burstable VMs for variable workloads
- Schedule VM shutdown during low-activity periods
- Monitor Azure costs and set alerts