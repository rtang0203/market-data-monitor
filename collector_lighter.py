import asyncio
import aiohttp
import psycopg2
import os
from datetime import datetime, timezone
from decimal import Decimal

# Database connection config (reads from env vars with defaults for local dev)
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'market_data'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'developmentPassword'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432'))
}

# Collection settings (reads from env var with default)
COLLECTION_INTERVAL = int(os.getenv('LIGHTER_COLLECTION_INTERVAL', '1800'))  # seconds (30 minutes)

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds between retries
TIMEOUT = 30  # seconds per request

# Exchange name mapping to distinguish from direct API sources
EXCHANGE_MAP = {
    'binance': 'binance_lighter',
    'bybit': 'bybit_lighter',
    'hyperliquid': 'hyperliquid_lighter',
    'lighter': 'lighter'
}


class LighterCollector:
    def __init__(self):
        self.api_url = 'https://mainnet.zklighter.elliot.ai/api/v1/funding-rates'

    def validate_response(self, data):
        """Validate API response format"""
        if not isinstance(data, dict):
            raise ValueError("Response must be a dictionary")

        if 'code' not in data:
            raise ValueError("Response missing 'code' field")

        if 'funding_rates' not in data:
            raise ValueError("Response missing 'funding_rates' field")

        if not isinstance(data['funding_rates'], list):
            raise ValueError("'funding_rates' must be a list")

        # Validate required fields in each funding rate record
        required_fields = ['market_id', 'exchange', 'symbol', 'rate']
        for i, record in enumerate(data['funding_rates']):
            if not all(field in record for field in required_fields):
                missing = [f for f in required_fields if f not in record]
                raise ValueError(f"Record {i} missing required fields: {missing}")

        return True

    async def fetch_funding_rates(self, session, retry_count=0):
        """
        Fetch funding rates from Lighter API with retry logic
        Returns dict of funding rate data for all exchanges/symbols
        """
        try:
            async with session.get(
                self.api_url,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Validate response format
                    self.validate_response(data)

                    return self.parse_response(data)
                else:
                    print(f"API error: HTTP {response.status}")
                    return None

        except asyncio.TimeoutError:
            print(f"Request timeout (attempt {retry_count + 1}/{MAX_RETRIES})")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self.fetch_funding_rates(session, retry_count + 1)
            else:
                print(f"Max retries exceeded for Lighter API")
                return None

        except Exception as e:
            print(f"Error fetching funding rates: {e}")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self.fetch_funding_rates(session, retry_count + 1)
            else:
                print(f"Max retries exceeded after error: {e}")
                return None

    def parse_response(self, data):
        """
        Parse Lighter API response into our data model
        Returns dict of funding rate data keyed by (exchange, symbol)
        """
        if not data or 'funding_rates' not in data:
            return {}

        funding_rates = data['funding_rates']
        results = dict()
        current_time = datetime.now(timezone.utc)

        for record in funding_rates:
            # Map exchange names to distinguish from direct sources
            original_exchange = record['exchange']
            mapped_exchange = EXCHANGE_MAP.get(original_exchange, original_exchange)

            symbol = record['symbol']
            key = (mapped_exchange, symbol)

            result = {
                'time': current_time,
                'exchange': mapped_exchange,
                'symbol': symbol,
                'funding_rate': Decimal(str(record['rate'])),
                'price': None,  # Not provided by Lighter API
                'volume_24h': None,
                'open_interest': None,
                'bid': None,
                'ask': None
            }
            results[key] = result

        return results


class DatabaseWriter:
    def __init__(self, config):
        self.config = config
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.config)
            print("Connected to database")
        except Exception as e:
            print(f"Database connection error: {e}")
            raise

    def is_connected(self):
        """Check if database connection is alive"""
        if not self.conn:
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            return True
        except Exception:
            return False

    def ensure_connection(self):
        """Ensure database connection is alive, reconnect if needed"""
        if not self.is_connected():
            print("Database connection lost, reconnecting...")
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
            self.connect()

    def insert_market_data_batch(self, data_list):
        """Insert multiple market data records in a single transaction"""
        if not data_list:
            return

        try:
            cursor = self.conn.cursor()

            query = """
                INSERT INTO market_data
                (time, exchange, symbol, price, volume_24h, open_interest, funding_rate, bid, ask)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Prepare batch data
            batch_data = [
                (
                    data['time'],
                    data['exchange'],
                    data['symbol'],
                    data['price'],
                    data['volume_24h'],
                    data['open_interest'],
                    data['funding_rate'],
                    data['bid'],
                    data['ask']
                )
                for data in data_list
            ]

            # Execute batch insert
            cursor.executemany(query, batch_data)
            self.conn.commit()
            cursor.close()

            print(f"Batch inserted {len(data_list)} funding rates from Lighter API at {data_list[0]['time'] if data_list else 'unknown time'}")

        except Exception as e:
            print(f"Error batch inserting data: {e}")
            self.conn.rollback()
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")


async def collect_data(collector, db_writer):
    """Collect funding rate data from Lighter API"""
    # Ensure database connection is alive
    db_writer.ensure_connection()

    async with aiohttp.ClientSession() as session:
        # Lighter API returns all exchanges/symbols in one call
        results = await collector.fetch_funding_rates(session)

        # Batch insert all results into database
        if results:
            data_list = list(results.values())
            db_writer.insert_market_data_batch(data_list)

            # Log exchange breakdown
            exchanges = {}
            for data in data_list:
                exchange = data['exchange']
                exchanges[exchange] = exchanges.get(exchange, 0) + 1
            print(f"Collected rates by exchange: {exchanges}")


async def main():
    """Main collection loop"""
    collector = LighterCollector()
    db_writer = DatabaseWriter(DB_CONFIG)

    try:
        db_writer.connect()

        print(f"Starting funding rate collection from Lighter API")
        print(f"Collection interval: {COLLECTION_INTERVAL} seconds")
        print(f"Exchange name mapping: {EXCHANGE_MAP}")

        while True:
            print(f"\n--- Collection run at {datetime.now(timezone.utc)} ---")
            await collect_data(collector, db_writer)
            await asyncio.sleep(COLLECTION_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping collector...")
    finally:
        db_writer.close()


if __name__ == "__main__":
    asyncio.run(main())
