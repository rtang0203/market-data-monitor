# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

##Instructions
- When writing code, please try to keep it as simple and readable as possible without introducing unnecessary complexity or verbosity.
- use datetime.datetime.now(datetime.timezone.utc) instead of datetime.datetime.utcnow()

## Project Overview

This is a market data monitoring system that collects cryptocurrency market data from exchanges and stores it in a PostgreSQL database. The current implementation includes a Hyperliquid exchange data collector.

**Current Status:**
- ✅ **Deployed on DigitalOcean** (production)
- ✅ Collecting **all symbols** from Hyperliquid every **30 minutes**
- ✅ Storing funding rates, open interest, volume, and pricing data
- ✅ Running 24/7 with Docker Compose auto-restart
- ✅ **Web dashboard** displaying top 10 long/short opportunities by 3-day average funding rates

## Architecture

- **Data Collection**: Asynchronous Python collectors that fetch market data from exchange APIs
- **Storage**: PostgreSQL/TimescaleDB database with optimized schema for time-series market data
- **Web Dashboard**: FastAPI backend + vanilla HTML/CSS/JS frontend for visualizing funding rate opportunities
- **Deployment**: Docker Compose orchestrating database, collector, and dashboard containers
- **Database Schema**: Single `market_data` table storing exchange, symbol, pricing, and volume data with time-series indexing
- **Collection Strategy**: Batch insert all symbols (200+) every 30 minutes for long-term trend analysis

## Key Components

- `collector_hyperliquid.py`: Main data collector for Hyperliquid exchange
  - `HyperliquidCollector`: Handles API calls and data parsing
  - `DatabaseWriter`: Manages PostgreSQL connections and data insertion
  - Async collection loop with configurable intervals
- `api/`: Web dashboard service
  - `main.py`: FastAPI backend with `/api/funding-rates` endpoint
  - `static/index.html`: Frontend dashboard UI with dark theme
  - Calculates 3-day average funding rates and returns top 10 long/short opportunities
- `init.sql`: Database schema initialization script

## Local Development

```bash
# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f collector

# Check data
docker exec crypto_db psql -U postgres -d market_data -c "SELECT COUNT(*) FROM market_data;"
```

## Production Deployment (DigitalOcean)

The application is deployed on DigitalOcean using Docker Compose:

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Navigate to project
cd market-data-monitor

# Start services
docker-compose up -d

# Update deployment (when code changes)
git pull
docker-compose up -d --build

# Access dashboard
# http://YOUR_DROPLET_IP:8080
```

**Configuration:**
- Database credentials stored in `.env` file (not in git)
- Environment variables for flexible configuration
- Auto-restart enabled for reliability
- Data persists in Docker volumes (safe during updates)

## Hyperliquid API Endpoints

#metaAndAssetCtxs -- can get current data for all symbols here

**Endpoint**: `POST https://api.hyperliquid.xyz/info`
**Headers**: `Content-Type: application/json`
**Request Body**: `{"type": "metaAndAssetCtxs"}`

**Response Structure**:
- Returns array with two elements:
  - `[0]`: Universe metadata (symbol names, decimals, max leverage)
  - `[1]`: Market data array (one object per symbol in universe order)

**Universe Fields**:
- 'name': Symbol name

**Market Data Fields**:
- `dayNtlVlm`: 24h notional volume
- `funding`: Current funding rate
- `impactPxs`: [bid impact price, ask impact price]
- `markPx`: Mark price
- `midPx`: Mid price
- `openInterest`: Open interest
- `oraclePx`: Oracle price
- `premium`: Premium rate
- `prevDayPx`: Previous day price

## Development Notes

- Database configuration reads from environment variables (with localhost defaults for local dev)
- Collection interval configurable via `COLLECTION_INTERVAL` environment variable (default: 1800 seconds)
- Batch insert optimization for efficient database writes
- Connection health checks and auto-reconnection for reliability
- Unit tests available in `tests/` directory
- The database schema supports optional TimescaleDB hypertable conversion for better time-series performance

## Next Steps

### Dashboard Enhancements
The basic funding rate dashboard is complete and deployed. Potential improvements:

- **Configurable time windows**: Add 1-day, 3-day, 7-day, and 30-day average options
- **Volume and OI filters**: Filter symbols by minimum volume or open interest thresholds
- **Alerts for extreme funding rates**: Email/webhook notifications when funding rates exceed thresholds
- **Historical charts**: Add Chart.js or similar to show funding rate trends over time
- **Symbol search and filtering**: Search bar and filters for specific symbols
- **Export capabilities**: CSV/JSON export of current data
- **Code organization**: Reorganize collector service into `collector/` folder (similar to `api/` structure)
- **Authentication**: Add basic auth for public deployment
- **Mobile optimization**: Improve responsive design for mobile devices