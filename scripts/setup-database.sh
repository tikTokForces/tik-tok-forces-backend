#!/bin/bash

# Database Setup Script for TikTok Forces API
# This script sets up PostgreSQL database

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

DB_NAME="tikforces"
DB_USER="tikforces"
PROJECT_DIR="/opt/tik_tok_forces_api"

echo -e "${GREEN}🗄️  Setting up PostgreSQL Database${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}📦 Installing PostgreSQL${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y postgresql postgresql-contrib
    elif command -v yum &> /dev/null; then
        yum install -y postgresql-server postgresql-contrib
        postgresql-setup --initdb
    fi
    systemctl enable postgresql
    systemctl start postgresql
fi

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create database and user
echo -e "${YELLOW}📝 Creating database and user${NC}"
sudo -u postgres psql << EOF
-- Create user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

# Update .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚙️  Updating .env file${NC}"
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME|" "$PROJECT_DIR/.env"
    echo -e "${GREEN}✅ Database credentials updated in .env${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found. Creating it...${NC}"
    cat > "$PROJECT_DIR/.env" << EOF
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
EOF
    chown tikforces:tikforces "$PROJECT_DIR/.env"
fi

echo -e "${GREEN}✅ Database setup completed!${NC}"
echo -e "${GREEN}📝 Database credentials:${NC}"
echo -e "   Database: $DB_NAME"
echo -e "   User: $DB_USER"
echo -e "   Password: $DB_PASSWORD"
echo -e "${YELLOW}⚠️  Save this password securely!${NC}"

