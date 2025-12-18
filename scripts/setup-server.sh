#!/bin/bash

# Initial Server Setup Script for TikTok Forces
# Run this script ONCE on a fresh Ubuntu server to set up the environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting TikTok Forces Server Setup${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}📦 Updating system packages${NC}"
apt-get update
apt-get upgrade -y

# Install system dependencies
echo -e "${YELLOW}📦 Installing system dependencies${NC}"
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    nginx \
    postgresql \
    postgresql-contrib \
    ffmpeg \
    git \
    curl \
    ufw \
    certbot \
    python3-certbot-nginx

# Install Node.js 20.x if not already installed
if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 20 ]; then
    echo -e "${YELLOW}📦 Installing Node.js 20.x${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

# Create project directories
echo -e "${YELLOW}📁 Creating project directories${NC}"
mkdir -p /opt/tik-tok-forces-backend
mkdir -p /opt/tik-tok-forces-frontend

# Setup PostgreSQL
echo -e "${YELLOW}🗄️  Setting up PostgreSQL${NC}"
sudo -u postgres psql << EOF
-- Create database and user
CREATE DATABASE tikforces;
CREATE USER tikforces WITH PASSWORD 'tikforces';
ALTER ROLE tikforces SET client_encoding TO 'utf8';
ALTER ROLE tikforces SET default_transaction_isolation TO 'read committed';
ALTER ROLE tikforces SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tikforces TO tikforces;
\q
EOF

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Setup Git repositories (manual step - user needs to clone)
echo -e "${YELLOW}📝 Git repositories setup${NC}"
echo -e "${GREEN}✅ Server setup completed!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "   1. Clone your repositories:"
echo -e "      cd /opt/tik-tok-forces-backend && git clone <your-backend-repo-url> ."
echo -e "      cd /opt/tik-tok-forces-frontend && git clone <your-frontend-repo-url> ."
echo -e "   2. Create .env file in backend:"
echo -e "      cd /opt/tik-tok-forces-backend"
echo -e "      nano .env"
echo -e "      Add: DATABASE_URL=postgresql+asyncpg://tikforces:tikforces@localhost:5432/tikforces"
echo -e "   3. Make deploy scripts executable:"
echo -e "      chmod +x /opt/tik-tok-forces-backend/scripts/deploy.sh"
echo -e "      chmod +x /opt/tik-tok-forces-frontend/scripts/deploy.sh"
echo -e "   4. Run initial deployment:"
echo -e "      /opt/tik-tok-forces-backend/scripts/deploy.sh"
echo -e "      API_URL=http://localhost:8000 /opt/tik-tok-forces-frontend/scripts/deploy.sh"

