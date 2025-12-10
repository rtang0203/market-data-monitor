# Dashboard Spec: Hyperliquid Funding Rate Monitor

## Overview

Build a web dashboard that displays the top 10 and bottom 10 cryptocurrencies by 3-day average funding rate, using data already being collected in PostgreSQL.

## Current State

- **Database**: PostgreSQL/TimescaleDB running in Docker (`crypto_db` container)
- **Table**: `market_data` with columns: `time`, `exchange`, `symbol`, `price`, `volume_24h`, `open_interest`, `funding_rate`, `bid`, `ask`
- **Data frequency**: Every 30 minutes (~48 rows per symbol per day)
- **Data available**: ~1.5 days currently, growing over time

## Requirements

### Backend (FastAPI)

Create `api/main.py` with a single endpoint:

```
GET /api/funding-rates
```

Returns JSON:
```json
{
  "updated_at": "2025-11-30T12:00:00Z",
  "top_10_long": [
    {"symbol": "LAYER", "funding_3d_avg": -0.13414, "data_points": 72},
    ...
  ],
  "top_10_short": [
    {"symbol": "ZEREBRO", "funding_3d_avg": 0.00457, "data_points": 72},
    ...
  ]
}
```

**Logic:**
- "Long opportunities" = most negative funding rates (you get paid to be long)
- "Short opportunities" = most positive funding rates (you get paid to be short)
- Calculate average of `funding_rate` over last 3 days (max 144 data points per symbol)
- Use whatever data is available if less than 3 days exists
- Include `data_points` count so UI can show data completeness

**SQL Query Approach:**
```sql
WITH recent_data AS (
  SELECT 
    symbol,
    funding_rate,
    time,
    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) as rn
  FROM market_data
  WHERE exchange = 'hyperliquid'
    AND time > NOW() - INTERVAL '3 days'
    AND funding_rate IS NOT NULL
)
SELECT 
  symbol,
  AVG(funding_rate) as funding_3d_avg,
  COUNT(*) as data_points
FROM recent_data
WHERE rn <= 144
GROUP BY symbol
ORDER BY funding_3d_avg ASC;  -- Most negative first for longs
```

### Frontend (Simple HTML/JS)

Create `api/static/index.html` - a single-page dashboard:

**Layout:**
- Header with title "Hyperliquid Funding Rates" and last updated timestamp
- Two side-by-side tables (or stacked on mobile):
  - Left (green header): "TOP 10 LONG" - most negative funding rates
  - Right (red header): "TOP 10 SHORT" - most positive funding rates

**Table columns:**
- Rank (1-10)
- Coin (symbol name)
- Funding 3-day avg % (formatted as percentage, e.g., -0.13414 displays as "-0.134%")
- Data status (show "Complete" if data_points >= 100, else show count)

**Styling:**
- Clean, dark theme similar to the screenshot (dark background, light text)
- Green tint for long table, red tint for short table
- No framework needed - vanilla CSS is fine
- Responsive: tables stack vertically on narrow screens

**Behavior:**
- Auto-refresh every 5 minutes
- Show loading state on initial load
- Show "Last updated: X minutes ago" in header

### File Structure

```
api/
  main.py          # FastAPI application
  requirements.txt # fastapi, uvicorn, psycopg2-binary
  Dockerfile       # Python container for API
  static/
    index.html     # Dashboard UI (served by FastAPI)
```

### Docker Integration

Add to existing `docker-compose.yml`:

```yaml
  dashboard:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: funding_dashboard
    restart: unless-stopped
    environment:
      DB_HOST: database
      DB_PORT: 5432
      DB_NAME: ${POSTGRES_DB:-market_data}
      DB_USER: ${POSTGRES_USER:-postgres}
      DB_PASSWORD: ${POSTGRES_PASSWORD:-developmentPassword}
    ports:
      - "8080:8080"
    depends_on:
      database:
        condition: service_healthy
```

### API Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### API requirements.txt

```
fastapi>=0.100.0
uvicorn>=0.23.0
psycopg2-binary>=2.9.0
```

## Implementation Notes

1. **Keep it simple**: This is a POC. No authentication, no caching layer, no complex state management.

2. **Database connection**: Use the same pattern as `collector_hyperliquid.py` - read from environment variables with localhost defaults for local dev.

3. **Error handling**: Basic try/catch, return empty arrays if DB query fails, log errors to stdout.

4. **Static file serving**: FastAPI can serve static files directly - mount `/static` and serve `index.html` at root.

5. **CORS**: Not needed since frontend is served from same origin.

6. **Funding rate display**: The raw values are decimals (e.g., 0.0001 = 0.01%). Multiply by 100 for percentage display.

## Testing

After implementation:

```bash
# Start everything
docker-compose up -d --build

# Check dashboard is running
curl http://localhost:8080/api/funding-rates

# Open browser to http://localhost:8080
```

## Future Enhancements (not for this PR)

- Historical charts per symbol
- Configurable time window (1d, 3d, 7d averages)
- Volume and OI filters
- Alerts for extreme funding rates
- Authentication for public deployment