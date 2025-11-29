import asyncio
import aiohttp
import sys
from pathlib import Path

# Add parent directory to path to import collector
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector_hyperliquid import HyperliquidCollector


async def main():
    """Test the API call using the production HyperliquidCollector"""
    collector = HyperliquidCollector()
    test_symbols = ['BTC', 'ETH', 'SOL']

    print("Testing Hyperliquid API...")
    print(f"Looking for symbols: {test_symbols}")
    print("-" * 50)

    async with aiohttp.ClientSession() as session:
        results = await collector.fetch_market_data(session)

        if results:
            print(f"\nSuccessfully parsed {len(results)} symbols")
            print("\nData for requested symbols:")

            for symbol in test_symbols:
                data = results.get(symbol)
                if data:
                    print(f"\n{symbol}:")
                    print(f"  Price: ${data['price']}")
                    print(f"  24h Volume: ${data['volume_24h']}")
                    print(f"  Open Interest: {data['open_interest']}")
                    print(f"  Funding Rate: {data['funding_rate']}")
                    print(f"  Bid: ${data['bid']}")
                    print(f"  Ask: ${data['ask']}")
                else:
                    print(f"\n{symbol}: NOT FOUND")

            print(f"\nAll available symbols: {list(results.keys())[:10]}...")  # Show first 10
        else:
            print("Failed to get data from API")


if __name__ == "__main__":
    asyncio.run(main())