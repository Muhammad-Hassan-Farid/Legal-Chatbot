#!/bin/bash

# PakLegal ChatBot Production Deployment Guide
# This script helps with initial deployment setup

set -e

echo "🚀 PakLegal ChatBot - Production Deployment Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_HOME="/home/paklegal/Pakistan-Constitution-Chatbot"
APP_USER="paklegal"
DOMAIN="${1:-paklegal-chatbot.com}"

echo -e "${YELLOW}Prerequisites:${NC}"
echo "✓ Ubuntu 20.04+ or similar Linux distribution"
echo "✓ Python 3.12 installed"
echo "✓ ffmpeg installed (brew install ffmpeg on macOS, apt-get install ffmpeg on Linux)"
echo "✓ PostgreSQL (optional, for production database)"
echo ""

# Step 1: Install system dependencies
echo -e "${YELLOW}Step 1: Installing system dependencies...${NC}"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv nginx git curl certbot python3-certbot-nginx ffmpeg
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "On macOS - ensure ffmpeg is installed via: brew install ffmpeg"
fi

# Step 2: Create application user
echo -e "${YELLOW}Step 2: Setting up application user...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash "$APP_USER"
    echo -e "${GREEN}✓ User $APP_USER created${NC}"
else
    echo -e "${GREEN}✓ User $APP_USER already exists${NC}"
fi

# Step 3: Setup virtual environment
echo -e "${YELLOW}Step 3: Setting up Python virtual environment...${NC}"
cd "$APP_HOME"
python3 -m venv myenv
source myenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Create .env file
echo -e "${YELLOW}Step 4: Creating environment file...${NC}"
if [ ! -f "$APP_HOME/.env" ]; then
    cat > "$APP_HOME/.env" << EOF
# Django Settings
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN
SECRET_KEY=$(openssl rand -base64 32)

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Database (optional, for production)
# DATABASE_URL=postgresql://user:password@localhost/paklegal_db
EOF
    echo -e "${GREEN}✓ .env file created - edit it with your settings${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Step 5: Collect static files
echo -e "${YELLOW}Step 5: Collecting static files...${NC}"
cd "$APP_HOME"
source myenv/bin/activate
python manage.py collectstatic --noinput

# Step 6: Setup Gunicorn
echo -e "${YELLOW}Step 6: Installing Gunicorn...${NC}"
pip install gunicorn

# Step 7: Setup systemd service
echo -e "${YELLOW}Step 7: Setting up systemd service...${NC}"
sudo cp "$APP_HOME/paklegal-chatbot.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable paklegal-chatbot.service
echo -e "${GREEN}✓ Systemd service configured${NC}"

# Step 8: Setup Nginx
echo -e "${YELLOW}Step 8: Configuring Nginx...${NC}"
sudo cp "$APP_HOME/nginx.conf" /etc/nginx/sites-available/paklegal-chatbot
sudo ln -sf /etc/nginx/sites-available/paklegal-chatbot /etc/nginx/sites-enabled/paklegal-chatbot
sudo nginx -t
echo -e "${GREEN}✓ Nginx configured${NC}"

# Step 9: Setup SSL with Let's Encrypt
echo -e "${YELLOW}Step 9: Setting up SSL certificate...${NC}"
echo "Run this command to setup SSL:"
echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"

# Step 10: Create log directories
echo -e "${YELLOW}Step 10: Creating log directories...${NC}"
sudo mkdir -p /var/log/gunicorn
sudo chown -R "$APP_USER:www-data" /var/log/gunicorn

# Final steps
echo ""
echo -e "${GREEN}✅ Deployment setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit .env file with your configuration:"
echo "   nano $APP_HOME/.env"
echo ""
echo "2. Setup SSL certificate:"
echo "   sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
echo "3. Start the application:"
echo "   sudo systemctl start paklegal-chatbot"
echo "   sudo systemctl restart nginx"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status paklegal-chatbot"
echo "   sudo journalctl -u paklegal-chatbot -f"
echo ""
echo "5. View application logs:"
echo "   sudo tail -f /var/log/gunicorn/error.log"
echo ""
