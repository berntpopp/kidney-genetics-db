# Production Deployment Guide

**Last Updated:** 2025-10-12
**Security Hardening:** ✅ Implemented (OWASP compliant)

Step-by-step guide for deploying Kidney Genetics Database to a VPS with Nginx Proxy Manager.

## 🔒 Security Features

This deployment includes comprehensive security hardening:
- ✅ Non-root containers (UID 1000 backend, UID 101 frontend)
- ✅ Linux capability dropping (principle of least privilege)
- ✅ SHA256 image pinning (supply chain protection)
- ✅ Resource limits (CPU, memory, PID limits)
- ✅ Security headers (OWASP-compliant)
- ✅ Automated vulnerability scanning (Trivy CI/CD)

For details, see [Security Implementation Summary](../implementation-notes/completed/docker-security-implementation-summary.md)

## Prerequisites

### On Your Local Machine
- [ ] Git access to repository
- [ ] SSH access to VPS
- [ ] Docker and Docker Compose installed locally (for testing)

### On Production VPS
- [ ] Ubuntu 22.04 LTS or similar (recommended)
- [ ] Docker Engine 24+ installed
- [ ] Docker Compose v2+ installed
- [ ] Nginx Proxy Manager (NPM) running
- [ ] `npm_proxy_network` Docker network created
- [ ] Domain DNS configured (A record pointing to VPS IP)
- [ ] At least 2GB RAM, 2 CPU cores, 20GB disk

### Required Access
- [ ] Root or sudo access on VPS
- [ ] SSH key authentication configured
- [ ] NPM admin panel access

---

## Part 1: Pre-Deployment Setup

### Step 1: Verify VPS Environment

SSH into your VPS:
```bash
ssh user@your-vps-ip
```

Check Docker installation:
```bash
docker --version
# Expected: Docker version 24.0.0 or higher

docker compose version
# Expected: Docker Compose version v2.20.0 or higher
```

### Step 2: Verify NPM Network

Check if `npm_proxy_network` exists:
```bash
docker network ls | grep npm_proxy_network
```

If not found, create it:
```bash
docker network create npm_proxy_network
```

Verify NPM is running:
```bash
docker ps | grep nginx-proxy-manager
```

### Step 3: Prepare Deployment Directory

Create application directory:
```bash
sudo mkdir -p /opt/kidney-genetics-db
sudo chown $USER:$USER /opt/kidney-genetics-db
cd /opt/kidney-genetics-db
```

---

## Part 2: Code and Configuration

### Step 4: Clone Repository

```bash
git clone https://github.com/bernt-popp/kidney-genetics-db.git .
# Or use SSH if configured:
# git clone git@github.com:bernt-popp/kidney-genetics-db.git .
```

Checkout production branch (if applicable):
```bash
git checkout main  # or your production branch
```

### Step 5: Create Production Environment File

Generate secure credentials:
```bash
# Database password
DB_PASS=$(openssl rand -base64 32)
echo "Database Password: $DB_PASS"

# Backend secret key
SECRET=$(openssl rand -hex 32)
echo "Secret Key: $SECRET"
```

Create `.env.production`:
```bash
cat > .env.production << EOF
# Database Configuration
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_user
POSTGRES_PASSWORD=$DB_PASS

# Database URL
DATABASE_URL=postgresql://kidney_user:$DB_PASS@kidney_genetics_postgres:5432/kidney_genetics

# Backend Configuration
SECRET_KEY=$SECRET
BACKEND_CORS_ORIGINS=[]
API_V1_STR=/api/v1
PROJECT_NAME=Kidney Genetics Database
LOG_LEVEL=INFO
LOG_FORMAT=json
ALLOWED_HOSTS=localhost,db.kidney-genetics.org

# Production domain
DOMAIN=db.kidney-genetics.org
EOF
```

**IMPORTANT:** Save these credentials securely! You'll need them for database access.

Set proper permissions:
```bash
chmod 600 .env.production
```

Verify file contents (check passwords are not "CHANGE_ME"):
```bash
grep -E "POSTGRES_PASSWORD|SECRET_KEY" .env.production
```

### Step 6: Update Domain Configuration

Edit `.env.production` to use your actual domain:
```bash
nano .env.production
# Change: DOMAIN=db.kidney-genetics.org
# To:     DOMAIN=your-actual-domain.com
# Also update ALLOWED_HOSTS
```

---

## Part 3: Build and Test

### Step 7: Build Docker Images

Build production images:
```bash
cd /opt/kidney-genetics-db
docker compose -f docker-compose.prod.yml build --no-cache
```

**Expected output:**
```
[+] Building 180.5s
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
kidney_genetics_backend    latest  <image-id>  X minutes ago  ~450MB
kidney_genetics_frontend   latest  <image-id>  X minutes ago  ~60MB
```

### Step 8: Test in Standalone Mode

Start in test mode (with exposed ports):
```bash
docker compose -f docker-compose.prod.test.yml up -d
```

Wait 30 seconds for services to start, then check health:
```bash
# Check containers
docker ps --filter "name=kidney_genetics"

# Test backend API
curl http://localhost:8001/health
# Expected: {"status":"healthy","service":"kidney-genetics-api","version":"0.1.0","database":"healthy"}

# Test frontend
curl http://localhost:8080/health
# Expected: {"status":"healthy","service":"kidney_genetics_frontend"}
```

If tests pass, stop test mode:
```bash
docker compose -f docker-compose.prod.test.yml down
```

If tests fail, check logs:
```bash
docker compose -f docker-compose.prod.test.yml logs
```

---

## Part 4: Production Deployment

### Step 9: Start Production Services

Start in NPM mode (no exposed ports):
```bash
docker compose -f docker-compose.prod.yml up -d
```

Verify containers are running:
```bash
docker ps --filter "name=kidney_genetics"
```

**Expected output:**
```
CONTAINER ID   IMAGE                             STATUS        NAMES
<id>           kidney_genetics_frontend:latest   Up X mins     kidney_genetics_frontend
<id>           kidney_genetics_backend:latest    Up X mins     kidney_genetics_backend
<id>           postgres:14-alpine                Up X mins     kidney_genetics_postgres
```

Check logs for errors:
```bash
docker compose -f docker-compose.prod.yml logs --tail=50
```

### Step 10: Configure Nginx Proxy Manager

Access NPM admin panel (usually at `http://your-vps-ip:81`):

#### For Frontend (Main Site)

1. **Add Proxy Host:**
   - Domain Names: `db.kidney-genetics.org`
   - Scheme: `http`
   - Forward Hostname/IP: `kidney_genetics_frontend`
   - Forward Port: `8080` ⚠️ **IMPORTANT: Changed from 80 to 8080 (security hardening)**
   - Cache Assets: ✅ Enabled
   - Block Common Exploits: ✅ Enabled
   - Websockets Support: ✅ Enabled (IMPORTANT!)

2. **SSL Certificate:**
   - SSL Tab → Request New SSL Certificate
   - Let's Encrypt
   - Email: your-email@example.com
   - Agree to Terms: ✅
   - Force SSL: ✅ Enabled

3. **Custom Nginx Config (Advanced Tab):**
   ```nginx
   # Increase client body size for file uploads
   client_max_body_size 10M;

   # WebSocket timeout settings
   proxy_read_timeout 3600s;
   proxy_send_timeout 3600s;
   ```

4. **Save**

#### For Backend API (Optional Direct Access)

If you need direct API access (usually not required as frontend proxies requests):

1. **Add Proxy Host:**
   - Domain Names: `api.db.kidney-genetics.org`
   - Scheme: `http`
   - Forward Hostname/IP: `kidney_genetics_backend`
   - Forward Port: `8000`
   - Websockets Support: ✅ Enabled

2. **SSL Certificate:**
   - Same process as frontend

---

## Part 5: Verification

### Step 11: Test Production Deployment

Wait 2 minutes for Let's Encrypt certificate provisioning.

Test HTTPS access:
```bash
# From VPS or local machine
curl -I https://db.kidney-genetics.org
# Expected: HTTP/2 200

curl https://db.kidney-genetics.org/health
# Expected: {"status":"healthy","service":"kidney_genetics_frontend"}

# Test backend API through frontend proxy
curl https://db.kidney-genetics.org/api/v1/health
# Expected: {"status":"healthy","service":"kidney-genetics-api","version":"0.1.0","database":"healthy"}
```

Test WebSocket connection (if applicable):
```bash
# Install wscat if not present:
npm install -g wscat

# Test WebSocket endpoint:
wscat -c wss://db.kidney-genetics.org/ws/test
# Should connect successfully
```

Open in browser:
```
https://db.kidney-genetics.org
```

**Expected:** Kidney Genetics Database homepage loads with HTTPS lock icon.

### Step 12: Verify Database

Connect to database:
```bash
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

Run verification queries:
```sql
-- Check tables exist
\dt

-- Check gene count (should be 0 initially, or populated if data imported)
SELECT COUNT(*) FROM genes;

-- Exit
\q
```

### Step 13: Monitor Logs

Check for errors in logs:
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Specific service
docker logs kidney_genetics_backend -f
docker logs kidney_genetics_frontend -f
docker logs kidney_genetics_postgres -f
```

---

## Part 6: Post-Deployment

### Step 14: Import Initial Data (if needed)

If you have a database dump:
```bash
# Copy dump to VPS
scp backup.sql user@vps:/tmp/

# Import
docker exec -i kidney_genetics_postgres psql \
  -U kidney_user kidney_genetics < /tmp/backup.sql
```

### Step 15: Setup Automated Backups

Create backup script:
```bash
sudo nano /opt/kidney-genetics-db/backup.sh
```

Add content:
```bash
#!/bin/bash
BACKUP_DIR="/opt/kidney-genetics-db/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kidney_genetics_$DATE.sql"

mkdir -p $BACKUP_DIR

docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user kidney_genetics > $BACKUP_FILE

gzip $BACKUP_FILE

# Keep only last 7 backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

Make executable:
```bash
chmod +x /opt/kidney-genetics-db/backup.sh
```

Add to crontab (daily at 2 AM):
```bash
crontab -e
```

Add line:
```cron
0 2 * * * /opt/kidney-genetics-db/backup.sh >> /opt/kidney-genetics-db/backup.log 2>&1
```

Test backup:
```bash
/opt/kidney-genetics-db/backup.sh
ls -lh /opt/kidney-genetics-db/backups/
```

### Step 16: Setup Monitoring (Optional)

Install monitoring tools:
```bash
# Docker stats
docker stats --no-stream kidney_genetics_backend kidney_genetics_frontend kidney_genetics_postgres

# Or setup continuous monitoring
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"'
```

### Step 17: Configure Firewall

Ensure only necessary ports are open:
```bash
# Check current rules
sudo ufw status

# Typical rules (adjust for your setup):
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (NPM)
sudo ufw allow 443/tcp    # HTTPS (NPM)
sudo ufw allow 81/tcp     # NPM admin (restrict to your IP!)

# Deny direct access to application ports
sudo ufw deny 8000/tcp    # Backend
sudo ufw deny 8080/tcp    # Frontend
sudo ufw deny 5432/tcp    # PostgreSQL

sudo ufw enable
```

---

## Maintenance Commands

### Update Application
```bash
cd /opt/kidney-genetics-db
git pull origin main
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f
```

### Restart Services
```bash
# All services
docker compose -f docker-compose.prod.yml restart

# Specific service
docker restart kidney_genetics_backend
```

### View Logs
```bash
# Follow logs
docker compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100

# Specific service
docker logs kidney_genetics_backend --tail=100 -f
```

### Stop/Start
```bash
# Stop
docker compose -f docker-compose.prod.yml stop

# Start
docker compose -f docker-compose.prod.yml start

# Stop and remove
docker compose -f docker-compose.prod.yml down
```

---

## Troubleshooting

### Issue: Containers won't start
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Check if network exists
docker network inspect npm_proxy_network

# Check if ports are in use
sudo netstat -tulpn | grep -E '8000|5432'
```

### Issue: NPM can't reach containers
```bash
# Verify containers are on npm_proxy_network
docker inspect kidney_genetics_frontend | grep npm_proxy_network

# Verify container names (use underscores!)
docker ps --format "table {{.Names}}\t{{.Networks}}"

# Test from NPM container
docker exec -it <npm-container> ping kidney_genetics_frontend
```

### Issue: Database connection fails
```bash
# Check database is healthy
docker inspect kidney_genetics_postgres | grep -A 10 Health

# Check logs
docker logs kidney_genetics_postgres

# Verify credentials in .env.production
grep DATABASE_URL .env.production
```

### Issue: SSL certificate fails
```bash
# Check DNS resolution
nslookup db.kidney-genetics.org

# Check port 80/443 are accessible
curl -I http://db.kidney-genetics.org
curl -I https://db.kidney-genetics.org

# Check NPM logs
docker logs <npm-container-name>
```

For more troubleshooting, see [Troubleshooting Guide](troubleshooting.md).

---

## Security Checklist

Post-deployment security verification:

- [ ] `.env.production` has secure credentials (not default values)
- [ ] `.env.production` has restricted permissions (600)
- [ ] SSL/TLS certificate is active and force-enabled
- [ ] Firewall rules restrict unnecessary ports
- [ ] Database is not directly accessible from internet
- [ ] NPM admin port (81) is restricted to your IP
- [ ] Automated backups are configured and tested
- [ ] Log rotation is enabled (default in docker-compose)
- [ ] Container healthchecks are passing
- [ ] WebSocket connections work correctly

---

## Next Steps

1. **Setup Admin User** - Create admin account in application
2. **Import Data** - Load gene data if not already present
3. **Configure Monitoring** - Setup uptime monitoring (UptimeRobot, etc.)
4. **Setup Alerts** - Configure alerts for service failures
5. **Document Credentials** - Store credentials securely (password manager)

---

## Reference

- [Docker Architecture](architecture.md) - Network and container design
- [Dockerfile Reference](dockerfile-reference.md) - Build configuration details
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [README](README.md) - Docker documentation index
