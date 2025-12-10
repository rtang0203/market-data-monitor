import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Hyperliquid Funding Rate Monitor")

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'market_data'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'developmentPassword')
}


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


@app.get("/api/funding-rates")
async def get_funding_rates() -> Dict[str, Any]:
    """
    Get top 10 long and short opportunities based on 3-day average funding rates.

    Returns:
        {
            "updated_at": ISO timestamp,
            "top_10_long": [...],  # Most negative funding (get paid to be long)
            "top_10_short": [...]  # Most positive funding (get paid to be short)
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query to calculate 3-day average funding rates
        query = """
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
            ORDER BY funding_3d_avg ASC;
        """

        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert to list of dicts
        all_symbols = [
            {
                "symbol": row['symbol'],
                "funding_3d_avg": float(row['funding_3d_avg']),
                "data_points": int(row['data_points'])
            }
            for row in results
        ]

        # Top 10 long opportunities (most negative funding rates)
        top_10_long = all_symbols[:10] if len(all_symbols) >= 10 else all_symbols

        # Top 10 short opportunities (most positive funding rates)
        top_10_short = all_symbols[-10:][::-1] if len(all_symbols) >= 10 else []

        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "top_10_long": top_10_long,
            "top_10_short": top_10_short
        }

    except Exception as e:
        logger.error(f"Error fetching funding rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funding-rates-by-exchange")
async def get_funding_rates_by_exchange() -> Dict[str, Any]:
    """
    Get top 10 long and short opportunities per exchange based on 3-day average funding rates.

    Returns:
        {
            "binance_lighter": {
                "long_opportunities": [...],
                "short_opportunities": [...]
            },
            "bybit_lighter": {...},
            "hyperliquid_lighter": {...},
            "hyperliquid": {...},
            "lighter": {...},
            "last_updated": ISO timestamp
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query to calculate 3-day average funding rates for all exchanges
        query = """
            WITH recent_data AS (
                SELECT
                    exchange,
                    symbol,
                    funding_rate,
                    time,
                    ROW_NUMBER() OVER (PARTITION BY exchange, symbol ORDER BY time DESC) as rn
                FROM market_data
                WHERE time > NOW() - INTERVAL '3 days'
                    AND funding_rate IS NOT NULL
            )
            SELECT
                exchange,
                symbol,
                AVG(funding_rate) as avg_funding_rate,
                COUNT(*) as data_points
            FROM recent_data
            WHERE rn <= 144  -- 3 days * 48 intervals/day (30 min)
            GROUP BY exchange, symbol
            ORDER BY exchange, avg_funding_rate ASC;
        """

        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert to list of dicts with float conversion
        all_data = [
            {
                "exchange": row['exchange'],
                "symbol": row['symbol'],
                "avg_funding_rate": float(row['avg_funding_rate']),
                "data_points": int(row['data_points'])
            }
            for row in results
        ]

        # Filter and sort by exchange using application-side logic
        response = {}
        exchanges = ['binance_lighter', 'bybit_lighter', 'hyperliquid_lighter', 'lighter', 'hyperliquid']

        for exchange in exchanges:
            exchange_data = [r for r in all_data if r['exchange'] == exchange]

            # Sort ascending for long opportunities (most negative rates)
            long_opps = sorted(exchange_data, key=lambda x: x['avg_funding_rate'])[:10]

            # Sort descending for short opportunities (most positive rates)
            short_opps = sorted(exchange_data, key=lambda x: x['avg_funding_rate'], reverse=True)[:10]

            response[exchange] = {
                'long_opportunities': long_opps,
                'short_opportunities': short_opps
            }
        
        # # NOW pop exchange from all responses
        # for exchange_data in response.values():
        #     for record in exchange_data['long_opportunities'] + exchange_data['short_opportunities']:
        #         record.pop('exchange', None)

        response['last_updated'] = datetime.now(timezone.utc).isoformat()

        return response

    except Exception as e:
        import traceback
        logger.error(f"Error fetching funding rates by exchange: {e}")
        logger.error(traceback.format_exc())  # Add this line for full traceback
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


# Mount static files and serve index.html at root
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root():
    """Serve the dashboard HTML at root path."""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
