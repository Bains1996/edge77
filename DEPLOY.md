# EDGE77 Deployment Guide

## What You Need to Do (30 minutes total)

### Step 1: Create Oracle Cloud Account (5 min)
1. Go to https://cloud.oracle.com
2. Click "Start for free"
3. Sign up with your email
4. Verify email → set password
5. Complete profile (use real info for verification)

### Step 2: Create SSH Key (1 min)
Open PowerShell on your laptop and run:
```powershell
ssh-keygen -t ed25519 -C "edge77" -f "$env:USERPROFILE\.ssh\edge77_key" -N ""
```
This creates two files:
- `edge77_key` (private key — keep safe)
- `edge77_key.pub` (public key — upload to Oracle)

### Step 3: Create VM (5 min)
1. In Oracle Cloud Dashboard → Compute → Instances → Create Instance
2. Name: `edge77`
3. Image: **Ubuntu 22.04** (click "Change image" → select Ubuntu)
4. Shape: **VM.Standard.A1.Flex** (click "Change shape" → select ARM)
5. Resources: **4 OCPUs, 24 GB RAM**
6. Under "Add SSH keys" → paste contents of `edge77_key.pub`
7. Click "Create"
8. Wait 2 min → copy the **Public IP address**

### Step 4: SSH into VM (1 min)
```powershell
ssh -i "$env:USERPROFILE\.ssh\edge77_key" ubuntu@<YOUR_PUBLIC_IP>
```

### Step 5: Deploy (5 min)
```bash
# Install git and clone
sudo apt update && sudo apt install -y git
git clone https://github.com/bainsarshveer/edge77.git
cd edge77

# Run deployment script
bash deploy/setup.sh
```
The script will:
- Install Python 3.12, nginx, certbot
- Create Python virtual environment
- Install all dependencies
- Create systemd service (auto-restart)
- Configure nginx reverse proxy
- Ask for your domain name

### Step 6: Edit .env (2 min)
```bash
nano .env
```
Fill in your API keys:
- `OPENROUTER_API_KEY` — from openrouter.ai/keys
- `SUPABASE_URL` — already set
- `SUPABASE_KEY` — already set
- `INTERNAL_API_TOKEN` — already set

Then restart:
```bash
sudo systemctl restart edge77
```

### Step 7: DNS (5 min)
1. Buy a domain (or use a free one from freenom.com)
2. In your domain's DNS settings, add:
   - Type: A
   - Name: @
   - Value: <YOUR_VM_IP>
3. Wait 5 min for propagation

### Step 8: SSL (2 min)
```bash
sudo certbot --nginx -d yourdomain.com
```

## Done!
- Landing: https://yourdomain.com
- Dashboard: https://yourdomain.com/dashboard
- API: https://yourdomain.com/v1/invoice/ingest
- Health: https://yourdomain.com/health

## Useful Commands
```bash
# Check status
sudo systemctl status edge77

# View logs
sudo journalctl -u edge77 -f

# Restart after code changes
cd ~/edge77 && git pull && sudo systemctl restart edge77

# Check nginx
sudo nginx -t && sudo systemctl reload nginx
```

## Costs
- Oracle Cloud Always Free: **$0/month forever**
- Domain: ~$10/year (optional — can use IP directly)
- OpenRouter: ~$0.28/truck/month (pay per use)
- Supabase Free: $0/month (500MB database)
