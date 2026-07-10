#!/bin/bash
# EDGE77 One-Command Deployment for Oracle Cloud Free
# Run this on your VM: bash deploy/setup.sh

set -e

echo "========================================="
echo "  EDGE77 — Oracle Cloud Free Deployment"
echo "========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# --- Step 1: System Update ---
echo -e "\n${YELLOW}[1/8] Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

# --- Step 2: Install Dependencies ---
echo -e "\n${YELLOW}[2/8] Installing Python 3.12, nginx, certbot...${NC}"
sudo apt install -y python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx git

# --- Step 3: Clone Repository ---
echo -e "\n${YELLOW}[3/8] Cloning Edge77 repository...${NC}"
if [ -d "/home/ubuntu/edge77" ]; then
    cd /home/ubuntu/edge77
    git pull
else
    cd /home/ubuntu
    git clone https://github.com/bainsarshveer/edge77.git
    cd edge77
fi

# --- Step 4: Setup Python Environment ---
echo -e "\n${YELLOW}[4/8] Setting up Python environment...${NC}"
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# --- Step 5: Configure Environment ---
echo -e "\n${YELLOW}[5/8] Configuring environment...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Edit .env with your actual API keys!${NC}"
    echo "  nano /home/ubuntu/edge77/.env"
    echo ""
    echo "Required keys:"
    echo "  - OPENROUTER_API_KEY"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_KEY"
    echo "  - INTERNAL_API_TOKEN"
    echo ""
    read -p "Press Enter after editing .env..."
fi

# --- Step 6: Create Systemd Service ---
echo -e "\n${YELLOW}[6/8] Creating systemd service...${NC}"
sudo tee /etc/systemd/system/edge77.service > /dev/null <<EOF
[Unit]
Description=EDGE77 Freight Auditor API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/edge77
ExecStart=/home/ubuntu/edge77/venv/bin/uvicorn v1_ingestion.main_gateway:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment=PATH=/home/ubuntu/edge77/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable edge77
sudo systemctl start edge77
echo -e "${GREEN}Edge77 service started!${NC}"

# --- Step 7: Configure Nginx ---
echo -e "\n${YELLOW}[7/8] Configuring nginx...${NC}"
read -p "Enter your domain name (or IP for now): " DOMAIN

sudo tee /etc/nginx/sites-available/edge77 > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/edge77 /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
echo -e "${GREEN}Nginx configured!${NC}"

# --- Step 8: SSL Certificate ---
echo -e "\n${YELLOW}[8/8] Setting up SSL...${NC}"
if [ "$DOMAIN" != "localhost" ] && [ "$DOMAIN" != "0.0.0.0" ]; then
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"
    echo -e "${GREEN}SSL certificate installed!${NC}"
else
    echo -e "${YELLOW}Skipping SSL (using IP address). Set up SSL later with:${NC}"
    echo "  sudo certbot --nginx -d yourdomain.com"
fi

# --- Done ---
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}  EDGE77 DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "  Landing page: http://$DOMAIN"
echo "  Dashboard:    http://$DOMAIN/dashboard"
echo "  Health:       http://$DOMAIN/health"
echo "  API docs:     http://$DOMAIN/docs"
echo ""
echo "  Service management:"
echo "    sudo systemctl status edge77"
echo "    sudo systemctl restart edge77"
echo "    sudo journalctl -u edge77 -f"
echo ""
