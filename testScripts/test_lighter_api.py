"""
Test script for Lighter API integration
Tests fetching, parsing, and data mapping
"""
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime, timezone

# Exchange name mapping (same as in collector)
EXCHANGE_MAP = {
    'binance': 'binance_lighter',
    'bybit': 'bybit_lighter',
    'hyperliquid': 'hyperliquid_lighter',
    'lighter': 'lighter'
}


async def test_lighter_api():
    """Test fetching and parsing Lighter API data"""
    url = 'https://mainnet.zklighter.elliot.ai/api/v1/funding-rates'

    print("=" * 60)
    print("LIGHTER API TEST")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            print(f"\n1. Fetching from: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    print(f"✗ API error: HTTP {response.status}")
                    return False

                print(f"✓ API fetch successful (HTTP {response.status})")

                data = await response.json()

                # Validate response structure
                print("\n2. Validating response structure:")
                if 'code' not in data:
                    print("✗ Missing 'code' field")
                    return False
                print(f"✓ Response code: {data['code']}")

                if 'funding_rates' not in data:
                    print("✗ Missing 'funding_rates' field")
                    return False
                print(f"✓ Found 'funding_rates' array")

                funding_rates = data['funding_rates']
                print(f"✓ Total funding rates: {len(funding_rates)}")

                # Check exchange breakdown
                print("\n3. Exchange breakdown:")
                exchanges = {}
                for record in funding_rates:
                    exchange = record['exchange']
                    exchanges[exchange] = exchanges.get(exchange, 0) + 1

                for exchange, count in sorted(exchanges.items()):
                    mapped = EXCHANGE_MAP.get(exchange, exchange)
                    print(f"  {exchange:15} → {mapped:20} ({count:3} symbols)")

                # Validate sample records
                print("\n4. Validating sample records:")
                required_fields = ['market_id', 'exchange', 'symbol', 'rate']

                for i in range(min(3, len(funding_rates))):
                    record = funding_rates[i]
                    missing = [f for f in required_fields if f not in record]

                    if missing:
                        print(f"✗ Record {i} missing fields: {missing}")
                        return False

                    print(f"✓ Record {i}: {record['exchange']:10} {record['symbol']:10} rate={record['rate']:+.8f}")

                # Test data mapping (as collector would do)
                print("\n5. Testing data mapping:")
                sample = funding_rates[0]
                mapped_exchange = EXCHANGE_MAP.get(sample['exchange'], sample['exchange'])

                mapped_data = {
                    'time': datetime.now(timezone.utc),
                    'exchange': mapped_exchange,
                    'symbol': sample['symbol'],
                    'funding_rate': Decimal(str(sample['rate'])),
                    'price': None,
                    'volume_24h': None,
                    'open_interest': None,
                    'bid': None,
                    'ask': None
                }

                print(f"✓ Mapped data structure:")
                print(f"  exchange: {mapped_data['exchange']}")
                print(f"  symbol: {mapped_data['symbol']}")
                print(f"  funding_rate: {mapped_data['funding_rate']}")
                print(f"  time: {mapped_data['time']}")

                # Check for unique assets (stocks, forex)
                print("\n6. Checking for unique assets:")
                unique_assets = []
                for record in funding_rates:
                    symbol = record['symbol']
                    # Stock symbols: AAPL, TSLA, etc.
                    # Forex symbols: EURUSD, GBPUSD, etc.
                    if 'USD' in symbol and len(symbol) == 6 and symbol[3:] == 'USD':
                        unique_assets.append(f"{symbol} (forex)")
                    elif symbol in ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'PLTR', 'HOOD', 'COIN']:
                        unique_assets.append(f"{symbol} (stock)")

                if unique_assets:
                    print(f"✓ Found {len(unique_assets)} unique assets:")
                    for asset in unique_assets[:10]:
                        print(f"  - {asset}")
                    if len(unique_assets) > 10:
                        print(f"  ... and {len(unique_assets) - 10} more")
                else:
                    print("  (No unique stock/forex assets found)")

                print("\n" + "=" * 60)
                print("ALL TESTS PASSED ✓")
                print("=" * 60)
                return True

        except asyncio.TimeoutError:
            print("✗ Request timeout")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_lighter_api())
    exit(0 if success else 1)
