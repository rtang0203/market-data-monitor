import asyncio
import aiohttp
from datetime import datetime, timezone
from decimal import Decimal


class HyperliquidTester:
    def __init__(self):
        self.exchange_name = 'hyperliquid'
        self.base_url = 'https://api.hyperliquid.xyz'

    async def fetch_market_data(self, session):
        """Fetch market data from Hyperliquid API"""
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {'type': 'metaAndAssetCtxs'}

            async with session.post(f'{self.base_url}/info',
                                  json=payload,
                                  headers=headers) as response:
                print(f"Response status: {response.status}")
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
        """Parse Hyperliquid API response"""
        if not data or len(data) < 2:
            return {}

        universe = data[0]['universe']
        market_data = data[1]

        results = dict()
        current_time = datetime.now(timezone.utc)

        print(f"Found {len(universe)} symbols in universe")
        print(f"Got market data for {len(market_data)} symbols")

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


async def main():
    """Test the API call"""
    tester = HyperliquidTester()
    test_symbols = ['BTC', 'ETH', 'SOL']

    print("Testing Hyperliquid API...")
    print(f"Looking for symbols: {test_symbols}")
    print("-" * 50)

    # # Create SSL context that doesn't verify certificates (for testing)
    # import ssl
    # ssl_context = ssl.create_default_context()
    # ssl_context.check_hostname = False
    # ssl_context.verify_mode = ssl.CERT_NONE

    # connector = aiohttp.TCPConnector(ssl=ssl_context)
    # async with aiohttp.ClientSession(connector=connector) as session:
    async with aiohttp.ClientSession() as session:
        results = await tester.fetch_market_data(session)

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