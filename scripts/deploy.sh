#!/bin/bash

# TikTok Forces API Deployment Script
# This script deploys the backend, frontend, and database on a Linux server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/tik_tok_forces_api"
SERVICE_USER="tikforces"
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_CONFIG="/etc/nginx/sites-available/tikforces"
NGINX_ENABLED="/etc/nginx/sites-enabled/tikforces"

echo -e "${GREEN}🚀 Starting TikTok Forces API Deployment${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Create service user if doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    echo -e "${YELLOW}📝 Creating service user: $SERVICE_USER${NC}"
    useradd -r -s /bin/bash -d "$PROJECT_DIR" "$SERVICE_USER"
fi

# Create project directory
echo -e "${YELLOW}📁 Creating project directory${NC}"
mkdir -p "$PROJECT_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"

# Install system dependencies
echo -e "${YELLOW}📦 Installing system dependencies${NC}"
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip python3-venv nodejs npm nginx postgresql-client ffmpeg git
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip nodejs npm nginx postgresql ffmpeg git
else
    echo -e "${RED}❌ Unsupported package manager${NC}"
    exit 1
fi

# Copy project files (assuming we're running from project root)
echo -e "${YELLOW}📋 Copying project files${NC}"
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Project already exists, updating..."
    cd "$PROJECT_DIR"
    sudo -u "$SERVICE_USER" git pull
else
    # Copy current directory to project directory
    cp -r . "$PROJECT_DIR/"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
fi

# Setup Python virtual environment
echo -e "${YELLOW}🐍 Setting up Python virtual environment${NC}"
cd "$PROJECT_DIR"
sudo -u "$SERVICE_USER" python3 -m venv venv
sudo -u "$SERVICE_USER" ./venv/bin/pip install --upgrade pip
sudo -u "$SERVICE_USER" ./venv/bin/pip install -r requirements.txt

# Setup Frontend
echo -e "${YELLOW}⚛️  Setting up Frontend${NC}"
cd "$PROJECT_DIR/frontend"
sudo -u "$SERVICE_USER" npm install
sudo -u "$SERVICE_USER" npm run build

# Setup environment file
echo -e "${YELLOW}⚙️  Setting up environment configuration${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo -e "${YELLOW}⚠️  Please edit $PROJECT_DIR/.env with your configuration${NC}"
    else
        cat > "$PROJECT_DIR/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://tikforces:changeme@localhost:5432/tikforces

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Environment
ENVIRONMENT=production
EOF
        chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/.env"
        echo -e "${YELLOW}⚠️  Please edit $PROJECT_DIR/.env with your database credentials${NC}"
    fi
fi

# Run database migrations
echo -e "${YELLOW}🗄️  Running database migrations${NC}"
cd "$PROJECT_DIR"
sudo -u "$SERVICE_USER" ./venv/bin/alembic upgrade head

# Setup systemd service for backend
echo -e "${YELLOW}🔧 Setting up systemd service${NC}"
cat > /etc/systemd/system/tikforces-backend.service << EOF
[Unit]
Description=TikTok Forces API Backend
After=network.target postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup Nginx configuration
echo -e "${YELLOW}🌐 Setting up Nginx${NC}"
cat > "$NGINX_CONFIG" << EOF
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        root $PROJECT_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Direct backend access (for compatibility)
    location ~ ^/(process|job|users|proxies|video|assets) {
        proxy_pass http://localhost:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # File upload size limit
    client_max_body_size 2G;
}
EOF

# Enable Nginx site
ln -sf "$NGINX_CONFIG" "$NGINX_ENABLED"
nginx -t && systemctl reload nginx

# Enable and start services
echo -e "${YELLOW}🔄 Starting services${NC}"
systemctl daemon-reload
systemctl enable tikforces-backend
systemctl restart tikforces-backend

# Check service status
if systemctl is-active --quiet tikforces-backend; then
    echo -e "${GREEN}✅ Backend service is running${NC}"
else
    echo -e "${RED}❌ Backend service failed to start. Check logs: journalctl -u tikforces-backend${NC}"
fi

echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${GREEN}📝 Next steps:${NC}"
echo -e "   1. Edit $PROJECT_DIR/.env with your database credentials"
echo -e "   2. Setup PostgreSQL database (see setup-database.sh)"
echo -e "   3. Check service status: systemctl status tikforces-backend"
echo -e "   4. View logs: journalctl -u tikforces-backend -f"
echo -e "   5. Access the application at http://your-server-ip"

