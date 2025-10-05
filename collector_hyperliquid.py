import asyncio
import aiohttp
import psycopg2
from datetime import datetime, timezone
from decimal import Decimal

# Database connection config
DB_CONFIG = {
    'dbname': 'market_data',
    'user': 'postgres',
    'password': 'developmentPassword',
    'host': 'localhost',
    'port': 5432
}

# Collection settings
SYMBOLS = ['BTC', 'ETH', 'SOL']  # Update with Hyperliquid format when ready
COLLECTION_INTERVAL = 60  # seconds


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
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")


async def collect_data(collector, db_writer):
    """Collect data for all symbols from Hyperliquid"""
    async with aiohttp.ClientSession() as session:
        # Hyperliquid returns all symbols in one API call
        results = await collector.fetch_market_data(session)

        # Insert results into database
        if results:
            for symbol in SYMBOLS:
                result = results.get(symbol)
                if result:
                    db_writer.insert_market_data(result)


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