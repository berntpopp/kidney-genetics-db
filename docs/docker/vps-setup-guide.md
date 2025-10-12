# VPS Setup Guide for Kidney Genetics Database

**Last Updated:** 2025-10-12
**Target OS:** Ubuntu 22.04 LTS (recommended) or Ubuntu 24.04 LTS
**Security:** OWASP-compliant Docker deployment

## Table of Contents

1. [VPS Requirements](#vps-requirements)
2. [Initial VPS Setup](#initial-vps-setup)
3. [Directory Structure](#directory-structure)
4. [File Creation](#file-creation)
5. [Docker Installation](#docker-installation)
6. [Nginx Proxy Manager Setup](#nginx-proxy-manager-setup)
7. [Application Deployment](#application-deployment)
8. [Security Configuration](#security-configuration)
9. [Verification](#verification)

---

## VPS Requirements

### Minimum Specifications
- **CPU:** 2 cores
- **RAM:** 2GB (4GB recommended for production)
- **Disk:** 20GB SSD (40GB+ recommended for data growth)
- **OS:** Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
- **Network:** Public IPv4 address with open ports 80, 443

### Recommended Specifications
- **CPU:** 4 cores
- **RAM:** 4GB
- **Disk:** 40GB+ SSD
- **Backup:** Automated VPS snapshots

### Provider Recommendations
- **Hetzner Cloud:** CPX21 (2 vCPU, 4GB RAM, €7.49/month)
- **DigitalOcean:** Basic Droplet (2 vCPU, 4GB RAM, $24/month)
- **Linode:** Dedicated 4GB (2 CPU, 4GB RAM, $24/month)
- **Vultr:** High Performance (2 vCPU, 4GB RAM, $24/month)

---

## Initial VPS Setup

### Step 1: Access Your VPS

```bash
# SSH into your VPS as root
ssh root@YOUR_VPS_IP
```

### Step 2: Create Non-Root User

```bash
# Create user
adduser deployer

# Add to sudo group
usermod -aG sudo deployer

# Switch to new user
su - deployer
```

### Step 3: Configure SSH Key Authentication

On your **local machine**:
```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key to VPS
ssh-copy-id deployer@YOUR_VPS_IP
```

Test key-based login:
```bash
ssh deployer@YOUR_VPS_IP
# Should not ask for password
```

### Step 4: Secure SSH Configuration

On VPS:
```bash
sudo nano /etc/ssh/sshd_config
```

Update these settings:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

### Step 5: Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget vim ufw fail2ban
```

### Step 6: Configure Firewall

```bash
# Allow SSH (IMPORTANT: Do this before enabling firewall!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS for NPM
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow NPM admin panel (restrict to your IP if possible)
sudo ufw allow 81/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

---

## Directory Structure

### Step 7: Create Directory Structure

```bash
# Create main application directory
sudo mkdir -p /opt/kidney-genetics-db
sudo chown deployer:deployer /opt/kidney-genetics-db

# Create subdirectories
mkdir -p /opt/kidney-genetics-db/{backups,logs,data}

# Create NPM directory (if not using Docker volume)
sudo mkdir -p /opt/nginx-proxy-manager/{data,letsencrypt}
sudo chown deployer:deployer /opt/nginx-proxy-manager -R

# Verify structure
tree -L 2 /opt/
```

**Expected structure:**
```
/opt/
├── kidney-genetics-db/
│   ├── backups/         # Database backups
│   ├── logs/            # Application logs (optional)
│   ├── data/            # Persistent data (optional)
│   ├── backend/         # Backend code (from git)
│   ├── frontend/        # Frontend code (from git)
│   ├── docker-compose.prod.yml
│   └── .env.production
└── nginx-proxy-manager/
    ├── data/            # NPM database
    └── letsencrypt/     # SSL certificates
```

---

## File Creation

### Step 8: Clone Repository

```bash
cd /opt/kidney-genetics-db
git clone https://github.com/bernt-popp/kidney-genetics-db.git .

# Or use SSH if configured
# git clone git@github.com:bernt-popp/kidney-genetics-db.git .

# Checkout appropriate branch
git checkout main  # or your production branch
```

### Step 9: Create Environment File

Generate secure credentials:
```bash
# Database password (32 bytes, base64 encoded)
DB_PASS=$(openssl rand -base64 32)
echo "Database Password: $DB_PASS"

# Backend secret key (64 hex characters)
SECRET=$(openssl rand -hex 32)
echo "Secret Key: $SECRET"

# IMPORTANT: Save these credentials in your password manager!
```

Create `.env.production`:
```bash
cat > /opt/kidney-genetics-db/.env.production << 'EOF'
# Database Configuration
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_user
POSTGRES_PASSWORD=REPLACE_WITH_DB_PASS

# Database URL
DATABASE_URL=postgresql://kidney_user:REPLACE_WITH_DB_PASS@kidney_genetics_postgres:5432/kidney_genetics

# Backend Configuration
SECRET_KEY=REPLACE_WITH_SECRET
BACKEND_CORS_ORIGINS=[]
API_V1_STR=/api/v1
PROJECT_NAME=Kidney Genetics Database
LOG_LEVEL=INFO
LOG_FORMAT=json
ALLOWED_HOSTS=localhost,your-domain.com

# Production domain
DOMAIN=your-domain.com
EOF
```

Replace placeholders:
```bash
# Replace REPLACE_WITH_DB_PASS with your generated password
sed -i "s/REPLACE_WITH_DB_PASS/$DB_PASS/g" /opt/kidney-genetics-db/.env.production

# Replace REPLACE_WITH_SECRET with your generated secret
sed -i "s/REPLACE_WITH_SECRET/$SECRET/g" /opt/kidney-genetics-db/.env.production

# Replace domain (replace your-domain.com with actual domain)
sed -i "s/your-domain.com/db.kidney-genetics.org/g" /opt/kidney-genetics-db/.env.production
```

Set proper permissions:
```bash
chmod 600 /opt/kidney-genetics-db/.env.production
chown deployer:deployer /opt/kidney-genetics-db/.env.production
```

Verify (should show actual passwords, not "REPLACE_WITH"):
```bash
grep -E "POSTGRES_PASSWORD|SECRET_KEY|DOMAIN" /opt/kidney-genetics-db/.env.production
```

### Step 10: Create Backup Script

```bash
cat > /opt/kidney-genetics-db/backup.sh << 'EOF'
#!/bin/bash
# Automated PostgreSQL backup script for Kidney Genetics Database

set -e

BACKUP_DIR="/opt/kidney-genetics-db/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kidney_genetics_$DATE.sql"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# Create backup
docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user kidney_genetics > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Calculate size
SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)

echo "[$(date)] Backup completed: $BACKUP_FILE.gz ($SIZE)"

# Remove old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Removed backups older than $RETENTION_DAYS days"

# Count remaining backups
COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "[$(date)] Total backups: $COUNT"
EOF

chmod +x /opt/kidney-genetics-db/backup.sh
```

### Step 11: Create Monitoring Script (Optional)

```bash
cat > /opt/kidney-genetics-db/monitor.sh << 'EOF'
#!/bin/bash
# Container health monitoring script

echo "=== Container Status ==="
docker ps --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
  kidney_genetics_backend kidney_genetics_frontend kidney_genetics_postgres

echo ""
echo "=== Health Checks ==="
curl -sf http://localhost:8001/health > /dev/null && echo "✓ Backend: Healthy" || echo "✗ Backend: Unhealthy"
curl -sf http://localhost:8080/health > /dev/null && echo "✓ Frontend: Healthy" || echo "✗ Frontend: Unhealthy"

echo ""
echo "=== Disk Usage ==="
df -h /opt/kidney-genetics-db /var/lib/docker
EOF

chmod +x /opt/kidney-genetics-db/monitor.sh
```

---

## Docker Installation

### Step 12: Install Docker Engine

```bash
# Remove old Docker versions (if any)
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker deployer

# Logout and login again for group changes to take effect
exit
ssh deployer@YOUR_VPS_IP
```

Verify installation:
```bash
docker --version
# Expected: Docker version 24.0.0 or higher

docker compose version
# Expected: Docker Compose version v2.20.0 or higher

# Test Docker
docker run hello-world
```

### Step 13: Configure Docker

Optional - Configure Docker daemon for better logging:
```bash
sudo mkdir -p /etc/docker

sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "10"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

---

## Nginx Proxy Manager Setup

### Step 14: Create NPM Network

```bash
# Create external network for NPM
docker network create npm_proxy_network

# Verify
docker network ls | grep npm_proxy_network
```

### Step 15: Deploy Nginx Proxy Manager

Create NPM docker-compose file:
```bash
sudo mkdir -p /opt/nginx-proxy-manager
sudo chown deployer:deployer /opt/nginx-proxy-manager

cat > /opt/nginx-proxy-manager/docker-compose.yml << 'EOF'
version: '3.8'

services:
  npm:
    image: 'jc21/nginx-proxy-manager:latest'
    container_name: nginx-proxy-manager
    restart: unless-stopped
    ports:
      - '80:80'      # HTTP
      - '443:443'    # HTTPS
      - '81:81'      # Admin panel
    environment:
      DB_SQLITE_FILE: "/data/database.sqlite"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
    networks:
      - npm_proxy_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:81"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  npm_proxy_network:
    external: true
EOF
```

Start NPM:
```bash
cd /opt/nginx-proxy-manager
docker compose up -d

# Wait 30 seconds for initialization
sleep 30

# Check status
docker ps | grep nginx-proxy-manager
```

### Step 16: Configure NPM Initial Setup

Access NPM admin panel: `http://YOUR_VPS_IP:81`

**Default credentials:**
- Email: `admin@example.com`
- Password: `changeme`

⚠️ **IMPORTANT:** Change these immediately on first login!

**Post-login steps:**
1. Update admin email
2. Change password to strong password
3. Enable 2FA (recommended)

---

## Application Deployment

### Step 17: Build Docker Images

```bash
cd /opt/kidney-genetics-db

# Build production images (this takes 5-10 minutes)
docker compose -f docker-compose.prod.yml build --no-cache
```

**Expected output:**
```
[+] Building 180.5s (37/37) FINISHED
 => [backend] exporting layers
 => [frontend] exporting layers
Successfully built images
```

Verify images:
```bash
docker images | grep kidney_genetics
```

**Expected:**
```
kidney_genetics_backend    latest   <id>   X minutes ago   ~450MB
kidney_genetics_frontend   latest   <id>   X minutes ago   ~60MB
```

### Step 18: Test Deployment (Optional but Recommended)

Test with exposed ports first:
```bash
docker compose -f docker-compose.prod.test.yml up -d

# Wait 30 seconds
sleep 30

# Check status
docker compose -f docker-compose.prod.test.yml ps

# Test health endpoints
curl http://localhost:8001/health
curl http://localhost:8080/health

# If working, stop test deployment
docker compose -f docker-compose.prod.test.yml down
```

### Step 19: Production Deployment

Start production stack (no port exposure):
```bash
docker compose -f docker-compose.prod.yml up -d

# Verify containers
docker ps --filter "name=kidney_genetics"
```

**Expected output:**
```
CONTAINER ID   IMAGE                             STATUS                   NAMES
<id>           kidney_genetics_frontend:latest   Up X minutes (healthy)   kidney_genetics_frontend
<id>           kidney_genetics_backend:latest    Up X minutes (healthy)   kidney_genetics_backend
<id>           postgres:14-alpine                Up X minutes (healthy)   kidney_genetics_postgres
```

Check logs for errors:
```bash
docker compose -f docker-compose.prod.yml logs --tail=50
```

### Step 20: Configure NPM Proxy

Access NPM admin panel: `http://YOUR_VPS_IP:81`

#### Add Proxy Host for Frontend

1. **Click "Proxy Hosts" → "Add Proxy Host"**

2. **Details Tab:**
   - Domain Names: `db.kidney-genetics.org` (your actual domain)
   - Scheme: `http`
   - Forward Hostname/IP: `kidney_genetics_frontend`
   - Forward Port: `8080` ⚠️ **Important: Use 8080, not 80**
   - Cache Assets: ✅ Enabled
   - Block Common Exploits: ✅ Enabled
   - Websockets Support: ✅ Enabled

3. **SSL Tab:**
   - SSL Certificate: "Request a new SSL Certificate"
   - Provider: Let's Encrypt
   - Email: your-email@example.com
   - Agree to Let's Encrypt Terms: ✅
   - Force SSL: ✅ Enabled

4. **Advanced Tab:**
   ```nginx
   # Increase client body size for file uploads
   client_max_body_size 10M;

   # WebSocket timeout settings
   proxy_read_timeout 3600s;
   proxy_send_timeout 3600s;
   ```

5. **Click "Save"**

Wait 2 minutes for SSL certificate provisioning.

---

## Security Configuration

### Step 21: Restrict NPM Admin Port

Restrict NPM admin panel (port 81) to your IP only:

```bash
# Get your public IP
curl ifconfig.me

# Block all access to port 81
sudo ufw deny 81/tcp

# Allow only from your IP (replace YOUR_IP)
sudo ufw allow from YOUR_IP to any port 81 proto tcp

# Reload firewall
sudo ufw reload

# Verify rules
sudo ufw status numbered
```

### Step 22: Verify Security Settings

```bash
# Check non-root containers
docker exec kidney_genetics_backend id
# Expected: uid=1000(kidney-api) gid=1000(kidney-api)

docker exec kidney_genetics_frontend id
# Expected: uid=101(nginx) gid=101(nginx)

# Check capability dropping
docker inspect kidney_genetics_backend | grep -A5 "CapDrop"
# Expected: "CapDrop": ["ALL"]

# Check security headers
curl -I https://db.kidney-genetics.org | grep -E "X-Frame|X-Content|Security-Policy"
# Should show multiple security headers

# Verify SHA256 pinning
docker inspect kidney_genetics_postgres | grep Image
# Should include @sha256:
```

### Step 23: Configure Automated Backups

Add backup to crontab:
```bash
crontab -e
```

Add this line (daily backup at 2 AM):
```cron
0 2 * * * /opt/kidney-genetics-db/backup.sh >> /opt/kidney-genetics-db/backup.log 2>&1
```

Test backup manually:
```bash
/opt/kidney-genetics-db/backup.sh
ls -lh /opt/kidney-genetics-db/backups/
```

### Step 24: Setup Log Rotation (Optional)

Docker handles log rotation, but you can configure custom rotation:

```bash
sudo nano /etc/logrotate.d/kidney-genetics
```

Add:
```
/opt/kidney-genetics-db/backup.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 deployer deployer
}
```

---

## Verification

### Step 25: Comprehensive Testing

#### Test HTTPS Access
```bash
curl -I https://db.kidney-genetics.org
# Expected: HTTP/2 200

curl https://db.kidney-genetics.org/health
# Expected: {"status":"healthy","service":"kidney_genetics_frontend"}
```

#### Test Backend API (through frontend proxy)
```bash
curl https://db.kidney-genetics.org/api/v1/health
# Expected: {"status":"healthy","service":"kidney-genetics-api","version":"0.1.0","database":"healthy"}
```

#### Test Database Connection
```bash
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

Run in psql:
```sql
-- Check tables
\dt

-- Check database size
SELECT pg_size_pretty(pg_database_size('kidney_genetics'));

-- Exit
\q
```

#### Test Security Headers
```bash
curl -I https://db.kidney-genetics.org | grep -E "X-Frame|X-Content|Security-Policy|Strict-Transport|Permissions"
```

**Expected headers:**
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Content-Security-Policy: default-src 'self'; ...
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()

#### Test WebSocket (if applicable)
```bash
# Install wscat
npm install -g wscat

# Test WebSocket connection
wscat -c wss://db.kidney-genetics.org/ws/test
```

#### Check Resource Usage
```bash
/opt/kidney-genetics-db/monitor.sh
```

### Step 26: Open in Browser

Navigate to: `https://db.kidney-genetics.org`

**Expected:**
- ✅ Loads with HTTPS (padlock icon)
- ✅ No SSL certificate warnings
- ✅ Application loads correctly
- ✅ Can interact with UI
- ✅ API calls work (check browser console)

---

## Post-Deployment Checklist

After deployment, verify:

- [ ] All containers are running and healthy
- [ ] HTTPS works with valid certificate
- [ ] Health endpoints respond correctly
- [ ] Database is accessible and initialized
- [ ] Security headers are present
- [ ] Firewall rules are configured
- [ ] NPM admin panel restricted to your IP
- [ ] Automated backups are configured
- [ ] Backup script tested successfully
- [ ] `.env.production` has secure permissions (600)
- [ ] Credentials saved in password manager
- [ ] Non-root containers verified
- [ ] Resource usage is acceptable
- [ ] WebSocket connections work (if applicable)
- [ ] DNS properly configured
- [ ] Logs are accessible

---

## Common Issues & Solutions

### Issue: Port 80/443 already in use

**Check what's using the ports:**
```bash
sudo netstat -tulpn | grep -E ':80|:443'
```

**Common culprit: Apache**
```bash
sudo systemctl stop apache2
sudo systemctl disable apache2
```

### Issue: NPM can't reach containers

**Verify network connectivity:**
```bash
# Check container networks
docker inspect kidney_genetics_frontend | grep -A10 Networks

# Test from NPM container
docker exec -it nginx-proxy-manager ping kidney_genetics_frontend
```

### Issue: SSL certificate fails

**Check DNS:**
```bash
nslookup db.kidney-genetics.org
# Should point to your VPS IP
```

**Check port 80 accessibility:**
```bash
curl -I http://db.kidney-genetics.org
# Should connect (may redirect to HTTPS)
```

### Issue: Database permission errors

**Fix volume permissions:**
```bash
docker compose -f docker-compose.prod.yml down -v
docker volume rm kidney_genetics_postgres_data
docker compose -f docker-compose.prod.yml up -d
```

---

## Maintenance Commands

### Update Application
```bash
cd /opt/kidney-genetics-db
git pull origin main
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### View Logs
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Specific service
docker logs kidney_genetics_backend -f
```

### Restart Services
```bash
# All services
docker compose -f docker-compose.prod.yml restart

# Specific service
docker restart kidney_genetics_frontend
```

### Manual Backup
```bash
/opt/kidney-genetics-db/backup.sh
```

### Restore Backup
```bash
# List backups
ls -lh /opt/kidney-genetics-db/backups/

# Restore (replace FILENAME)
gunzip -c /opt/kidney-genetics-db/backups/FILENAME.sql.gz | \
  docker exec -i kidney_genetics_postgres psql -U kidney_user kidney_genetics
```

---

## Next Steps

1. **Setup Monitoring:** Configure uptime monitoring (UptimeRobot, etc.)
2. **Configure Alerts:** Email/SMS alerts for service failures
3. **Import Data:** Load initial gene data if applicable
4. **Create Admin User:** Set up first admin account
5. **Test Thoroughly:** Comprehensive functionality testing
6. **Document:** Keep deployment notes for your specific configuration

---

## Support & Documentation

- **Production Deployment:** [production-deployment.md](production-deployment.md)
- **Security Implementation:** [../implementation-notes/completed/docker-security-implementation-summary.md](../implementation-notes/completed/docker-security-implementation-summary.md)
- **Troubleshooting:** [troubleshooting.md](troubleshooting.md)
- **Docker Architecture:** [architecture.md](architecture.md)

---

**Deployment Complete! 🎉**

Your Kidney Genetics Database is now running securely on your VPS with OWASP-compliant Docker security hardening.
