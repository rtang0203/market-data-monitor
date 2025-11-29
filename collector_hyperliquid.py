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
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '1800'))  # seconds (30 minutes)


class HyperliquidCollector:
    def __init__(self):
        self.exchange_name = 'hyperliquid'
        self.base_url = 'https://api.hyperliquid.xyz'
        
    async def fetch_market_data(self, session):
        """
        Fetch market data from Hyperliquid API
        Note: Hyperliquid returns data for all symbols in one call
        """
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {'type': 'metaAndAssetCtxs'}

            async with session.post(f'{self.base_url}/info',
                                  json=payload,
                                  headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.parse_response(data)
                else:
                    print(f"API error: {response.status}")
                    return None

        except Exception as e:
            print(f"Error fetching market data: {e}")
            return None
    
    def parse_response(self, data):
        """
        Parse Hyperliquid API response into our data model
        Returns dict of market data for all symbols
        """
        if not data or len(data) < 2:
            return {}

        universe = data[0]['universe']
        market_data = data[1]

        results = dict()
        current_time = datetime.now(timezone.utc)

        for i, symbol_info in enumerate(universe):
            if i >= len(market_data):
                continue

            symbol_name = symbol_info['name']
            market_info = market_data[i]

            # Extract bid/ask from impact prices
            bid = Decimal(market_info['impactPxs'][0]) if market_info.get('impactPxs') else None
            ask = Decimal(market_info['impactPxs'][1]) if market_info.get('impactPxs') and len(market_info['impactPxs']) > 1 else None

            result = {
                'time': current_time,
                'exchange': self.exchange_name,
                'symbol': symbol_name,
                'price': Decimal(market_info['markPx']) if market_info.get('markPx') else None,
                'volume_24h': Decimal(market_info['dayNtlVlm']) if market_info.get('dayNtlVlm') else None,
                'open_interest': Decimal(market_info['openInterest']) if market_info.get('openInterest') else None,
                'funding_rate': Decimal(market_info['funding']) if market_info.get('funding') else None,
                'bid': bid,
                'ask': ask
            }
            results[symbol_name] = result

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

    def insert_market_data(self, data):
        """Insert market data into database"""
        if not data:
            return

        try:
            cursor = self.conn.cursor()

            query = """
                INSERT INTO market_data
                (time, exchange, symbol, price, volume_24h, open_interest, funding_rate, bid, ask)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                data['time'],
                data['exchange'],
                data['symbol'],
                data['price'],
                data['volume_24h'],
                data['open_interest'],
                data['funding_rate'],
                data['bid'],
                data['ask']
            ))

            self.conn.commit()
            cursor.close()
            print(f"Inserted data for {data['symbol']} at {data['time']}")

        except Exception as e:
            print(f"Error inserting data: {e}")
            self.conn.rollback()

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

            print(f"Batch inserted {len(data_list)} symbols at {data_list[0]['time'] if data_list else 'unknown time'}")

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
    """Collect data for all symbols from Hyperliquid"""
    # Ensure database connection is alive
    db_writer.ensure_connection()

    async with aiohttp.ClientSession() as session:
        # Hyperliquid returns all symbols in one API call
        results = await collector.fetch_market_data(session)

        # Batch insert all results into database
        if results:
            data_list = list(results.values())
            db_writer.insert_market_data_batch(data_list)


async def main():
    """Main collection loop"""
    collector = HyperliquidCollector()
    db_writer = DatabaseWriter(DB_CONFIG)
    
    try:
        db_writer.connect()
        
        print(f"Starting data collection from Hyperliquid")
        print(f"Collection interval: {COLLECTION_INTERVAL} seconds")

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