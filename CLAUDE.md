# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Instructions

- Keep code simple and readable without unnecessary complexity
- Use `datetime.datetime.now(datetime.timezone.utc)` instead of `datetime.datetime.utcnow()`

## Project Overview

Market data monitoring system that collects cryptocurrency funding rates from exchanges and stores them in PostgreSQL/TimescaleDB.

**Current Status:**
- ✅ Deployed on DigitalOcean droplet
- ✅ Collecting from Hyperliquid (direct) and Lighter API (Binance, Bybit, Hyperliquid, Lighter)
- ✅ Web dashboard at port 8080
- ✅ Auto-cleanup of data older than 7 days via cron

## Architecture

- **Database**: TimescaleDB in Docker container
- **Collectors**: Python scripts running via systemd
- **Dashboard**: FastAPI + vanilla HTML/JS running via systemd
- **Data retention**: 7 days (cron job cleans old data daily)

## Key Files

- `collector_hyperliquid.py` - Hyperliquid direct API collector
- `collector_lighter.py` - Lighter API collector (multiple exchanges)
- `api/main.py` - FastAPI dashboard backend
- `api/static/index.html` - Dashboard frontend
- `docker-compose.yml` - Database only
- `systemd/` - Service files for collectors and dashboard
- `init.sql` - Database schema

## Local Development
```bash
# Start database
docker-compose up -d

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run collectors (in separate terminals)
export $(cat .env | xargs)
python collector_hyperliquid.py
python collector_lighter.py

# Run dashboard
cd api
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Deployment (Droplet)
```bash
# SSH in
ssh root@YOUR_DROPLET_IP
cd ~/market-data-monitor

# Update code
git pull

# Restart services
systemctl restart collector-hyperliquid collector-lighter funding-dashboard

# Check status
systemctl status collector-hyperliquid
journalctl -u collector-hyperliquid -f
```

## Environment Variables

Configured in `.env` (not in git):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `COLLECTION_INTERVAL`, `LIGHTER_COLLECTION_INTERVAL`

## Useful Commands
```bash
# Check services
systemctl status collector-hyperliquid collector-lighter funding-dashboard

# View logs
journalctl -u collector-hyperliquid -f

# Database queries
docker exec crypto_db psql -U postgres -d market_data -c "SELECT COUNT(*) FROM market_data;"

# Check disk usage
df -h
```
## Next Steps

### Dashboard Enhancements

The basic funding rate dashboard is complete and deployed. Potential improvements:

- **Configurable time windows**: Add 1-day, current average options
- **Volume and OI filters**: Filter symbols by minimum volume or open interest thresholds
- **Alerts for extreme funding rates**: Email/webhook notifications when funding rates exceed thresholds
- **Historical charts**: Add Chart.js or similar to show funding rate trends over time
- **Symbol search and filtering**: Search bar and filters for specific symbols
- **Code organization**: Reorganize collector service into `collector/` folder (similar to `api/` structure)
- **Authentication**: Add basic auth for public deployment
