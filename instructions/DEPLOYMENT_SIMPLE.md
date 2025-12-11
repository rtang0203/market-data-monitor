# Simplified Deployment Guide

This guide covers running the market data monitor with Docker for the database and systemd for the Python scripts.

## Step 1: Edit docker-compose.yml locally

Replace your current `docker-compose.yml` with database-only:

```yaml
services:
  database:
    image: timescale/timescaledb:latest-pg15
    container_name: crypto_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-market_data}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-developmentPassword}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  postgres_data:
    driver: local
```

## Step 2: Create .env files

Create a `.env` file for local development:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=developmentPassword
COLLECTION_INTERVAL=1800
LIGHTER_COLLECTION_INTERVAL=1800
```

Make sure `.env` is in your `.gitignore` so it doesn't get committed.

## Step 3: Test locally

```bash
cd ~/path/to/market-data-monitor

# Stop any running containers
docker-compose down

# Start just the database
docker-compose up -d

# Verify it's running
docker ps
```

Set up Python environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Test each script (in separate terminal windows, or one at a time):

```bash
source venv/bin/activate
export $(cat .env | xargs)

# Test collector
python collector_hyperliquid.py

# Test lighter collector (in another terminal)
python collector_lighter.py

# Test dashboard (in another terminal)
cd api
uvicorn main:app --host 0.0.0.0 --port 8080
```

Make sure each one connects to the database and runs without errors. Ctrl+C to stop each one after confirming it works.

## Step 4: Create systemd service files locally

Create a `systemd/` folder in your project:

```bash
mkdir systemd
```

Create three files:

### systemd/collector-hyperliquid.service

```ini
[Unit]
Description=Hyperliquid Funding Rate Collector
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/market-data-monitor
EnvironmentFile=/root/market-data-monitor/.env
ExecStart=/root/market-data-monitor/.venv/bin/python collector_hyperliquid.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### systemd/collector-lighter.service

```ini
[Unit]
Description=Lighter API Funding Rate Collector
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/market-data-monitor
EnvironmentFile=/root/market-data-monitor/.env
ExecStart=/root/market-data-monitor/.venv/bin/python collector_lighter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### systemd/funding-dashboard.service

```ini
[Unit]
Description=Funding Rate Dashboard API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/market-data-monitor/api
EnvironmentFile=/root/market-data-monitor/.env
ExecStart=/root/market-data-monitor/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Step 5: Push to git

```bash
git add docker-compose.yml systemd/
git commit -m "Simplify: database in Docker, Python scripts via systemd"
git push
```

## Step 6: Set up on droplet

SSH into your droplet:

```bash
ssh root@your-droplet-ip
```

Stop and clean up old containers:

```bash
cd ~/market-data-monitor
docker-compose down
docker system prune -a  # optional: clean up old images
```

Pull latest code:

```bash
git pull
```

Create the production `.env` file on the droplet:

```bash
cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=yourProductionPassword
COLLECTION_INTERVAL=1800
LIGHTER_COLLECTION_INTERVAL=1800
EOF
```

Start the database:

```bash
docker-compose up -d
docker ps  # verify it's running
```

Set up Python environment:

```bash
apt update && apt install -y python3-venv python3-pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install the systemd services:

```bash
cp systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable collector-hyperliquid collector-lighter funding-dashboard
systemctl start collector-hyperliquid collector-lighter funding-dashboard
```

Verify everything is running:

```bash
systemctl status collector-hyperliquid
systemctl status collector-lighter
systemctl status funding-dashboard
```

## Quick Reference

### Service management

| Task | Command |
|------|---------|
| Check service status | `systemctl status collector-hyperliquid` |
| View live logs | `journalctl -u collector-hyperliquid -f` |
| Restart a service | `systemctl restart collector-hyperliquid` |
| Stop a service | `systemctl stop collector-hyperliquid` |
| Restart all three | `systemctl restart collector-hyperliquid collector-lighter funding-dashboard` |

### Database management

| Task | Command |
|------|---------|
| Check database | `docker ps` |
| Database logs | `docker-compose logs -f` |
| Restart database | `docker-compose restart` |

## Future Deployments

After making code changes:

```bash
# Local
git add .
git commit -m "your changes"
git push

# Droplet
cd ~/market-data-monitor
git pull
systemctl restart collector-hyperliquid collector-lighter funding-dashboard
```

No more building or pushing Docker images.

## Updating Environment Variables

If you need to change environment variables on the droplet:

```bash
# Edit the .env file
nano ~/market-data-monitor/.env

# Restart services to pick up changes
systemctl restart collector-hyperliquid collector-lighter funding-dashboard
```

## Automatic Data Cleanup

To prevent the droplet from running out of disk space, a cron job deletes data older than 7 days.

### Setup (one-time on droplet)

Create the cleanup script:
```bash
nano ~/market-data-monitor/cleanup_old_data.sh
```
```bash
#!/bin/bash
docker exec crypto_db psql -U postgres -d market_data -c "DELETE FROM market_data WHERE time < NOW() - INTERVAL '7 days';"
echo "$(date): Cleaned up old data" >> /var/log/market-data-cleanup.log
```

Make it executable:
```bash
chmod +x ~/market-data-monitor/cleanup_old_data.sh
```

Add to cron (runs daily at 3am):
```bash
crontab -e
```
```
0 3 * * * /root/market-data-monitor/cleanup_old_data.sh
```

### Monitoring
```bash
# Check cleanup history
cat /var/log/market-data-cleanup.log

# Check cron is set
crontab -l

# Check current data size
docker exec crypto_db psql -U postgres -d market_data -c "SELECT COUNT(*) FROM market_data;"
```