# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

##Instructions
- When writing code, please try to keep it as simple and readable as possible without introducing unnecessary complexity or verbosity.
- use datetime.datetime.now(datetime.timezone.utc) instead of datetime.datetime.utcnow()

## Project Overview

This is a market data monitoring system that collects cryptocurrency market data from exchanges and stores it in a PostgreSQL database. The current implementation includes a Hyperliquid exchange data collector.

## Architecture

- **Data Collection**: Asynchronous Python collectors that fetch market data from exchange APIs
- **Storage**: PostgreSQL database with optimized schema for time-series market data
- **Database Schema**: Single `market_data` table storing exchange, symbol, pricing, and volume data with time-series indexing

## Key Components

- `collector_hyperliquid.py`: Main data collector for Hyperliquid exchange
  - `HyperliquidCollector`: Handles API calls and data parsing
  - `DatabaseWriter`: Manages PostgreSQL connections and data insertion
  - Async collection loop with configurable intervals
- `init.sql`: Database schema initialization script

## Database Setup

The database runs in Docker using TimescaleDB:

```bash
# Start the database container
docker run -d \
  --name crypto_db \
  --restart unless-stopped \
  -e POSTGRES_PASSWORD=developmentPassword \
  -e POSTGRES_DB=market_data \
  -p 5432:5432 \
  -v crypto_data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg15

# Initialize the database schema
docker exec -i crypto_db psql -U postgres -d market_data < init.sql
```

Database connection settings:
- Database: `market_data`
- User: `postgres`
- Password: `developmentPassword`
- Host: `localhost`
- Port: `5432`

## Running the Collector

```bash
# Run the main data collector
python collector_hyperliquid.py
```

The collector runs continuously, fetching data every 10 seconds by default for BTC-USD, ETH-USD, and SOL-USD symbols.

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

- Database configuration is hardcoded in `collector_hyperliquid.py` (DB_CONFIG)
- Collection interval and symbols are configurable via constants at the top of the collector file
- The database schema supports optional TimescaleDB hypertable conversion for better time-series performance