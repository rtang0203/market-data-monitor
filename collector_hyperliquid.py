import asyncio
import aiohttp
import psycopg2
from datetime import datetime
from decimal import Decimal

# Database connection config
DB_CONFIG = {
    'dbname': 'market_data',
    'user': 'your_user',
    'password': 'your_password',
    'host': 'localhost',
    'port': 5432
}

# Collection settings
SYMBOLS = ['BTC-USD', 'ETH-USD', 'SOL-USD']  # Update with Hyperliquid format when ready
COLLECTION_INTERVAL = 10  # seconds


class HyperliquidCollector:
    def __init__(self):
        self.exchange_name = 'hyperliquid'
        self.base_url = 'https://api.hyperliquid.xyz'  # Placeholder - update with real URL
        
    async def fetch_market_data(self, session, symbol):
        """
        Fetch market data for a symbol from Hyperliquid API
        
        TODO: Update with actual Hyperliquid API endpoints
        """
        try:
            # Placeholder for API call - we'll fill this in with real endpoints
            # async with session.get(f'{self.base_url}/endpoint?symbol={symbol}') as response:
            #     data = await response.json()
            #     return self.parse_response(data, symbol)
            
            # For now, return None - we'll implement this once you provide the API details
            print(f"Fetching data for {symbol} from {self.exchange_name}")
            return None
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def parse_response(self, data, symbol):
        """
        Parse API response into our data model
        
        TODO: Update based on actual Hyperliquid API response structure
        """
        # This will be filled in based on the actual API response format
        return {
            'time': datetime.utcnow(),
            'exchange': self.exchange_name,
            'symbol': symbol,
            'price': None,  # Extract from data
            'volume_24h': None,
            'open_interest': None,
            'funding_rate': None,
            'bid': None,
            'ask': None
        }


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


async def collect_data(collector, db_writer, symbols):
    """Collect data for all symbols"""
    async with aiohttp.ClientSession() as session:
        tasks = [collector.fetch_market_data(session, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        # Insert results into database
        for result in results:
            if result:
                db_writer.insert_market_data(result)


async def main():
    """Main collection loop"""
    collector = HyperliquidCollector()
    db_writer = DatabaseWriter(DB_CONFIG)
    
    try:
        db_writer.connect()
        
        print(f"Starting data collection for {len(SYMBOLS)} symbols")
        print(f"Collection interval: {COLLECTION_INTERVAL} seconds")
        
        while True:
            print(f"\n--- Collection run at {datetime.utcnow()} ---")
            await collect_data(collector, db_writer, SYMBOLS)
            await asyncio.sleep(COLLECTION_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping collector...")
    finally:
        db_writer.close()


if __name__ == "__main__":
    asyncio.run(main())