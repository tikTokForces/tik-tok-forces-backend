#!/bin/bash

# TikTok Forces Backend Deployment Script
# This script deploys the backend on a Linux server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/tik-tok-forces-backend"
SERVICE_NAME="tikforces-backend"
BACKEND_PORT=8000

echo -e "${GREEN}🚀 Starting TikTok Forces Backend Deployment${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Setup Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🐍 Creating Python virtual environment${NC}"
    python3 -m venv venv
fi

# Activate virtual environment and install/update dependencies
echo -e "${YELLOW}📦 Installing/updating Python dependencies${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo -e "${YELLOW}🗄️  Running database migrations${NC}"
alembic upgrade head

# Setup systemd service if it doesn't exist
if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    echo -e "${YELLOW}🔧 Setting up systemd service${NC}"
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=TikTok Forces API Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="DATABASE_URL=\${DATABASE_URL:-postgresql+asyncpg://tikforces:tikforces@localhost:5432/tikforces}"
Environment="VIDEO_PROCESSOR_BASE=\${VIDEO_PROCESSOR_BASE:-/opt/tik-tok-forces-video-processor}"
Environment="VIDEO_PROCESSOR_VENV=\${VIDEO_PROCESSOR_VENV:-/opt/tik-tok-forces-video-processor/.venv/bin/python}"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
else
    # Update existing service file with new environment variables
    echo -e "${YELLOW}🔄 Updating systemd service environment${NC}"
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=TikTok Forces API Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="DATABASE_URL=\${DATABASE_URL:-postgresql+asyncpg://tikforces:tikforces@localhost:5432/tikforces}"
Environment="VIDEO_PROCESSOR_BASE=\${VIDEO_PROCESSOR_BASE:-/opt/tik-tok-forces-video-processor}"
Environment="VIDEO_PROCESSOR_VENV=\${VIDEO_PROCESSOR_VENV:-/opt/tik-tok-forces-video-processor/.venv/bin/python}"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
fi

# Restart service
echo -e "${YELLOW}🔄 Restarting service${NC}"
systemctl restart "${SERVICE_NAME}"

# Wait a moment and check service status
sleep 3
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo -e "${GREEN}✅ Backend service is running${NC}"
    systemctl status "${SERVICE_NAME}" --no-pager -l
else
    echo -e "${RED}❌ Backend service failed to start${NC}"
    echo -e "${YELLOW}📋 Checking logs...${NC}"
    journalctl -u "${SERVICE_NAME}" -n 50 --no-pager
    exit 1
fi

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
