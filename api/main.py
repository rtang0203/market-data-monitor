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
