import unittest
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collector_hyperliquid import HyperliquidCollector


class TestHyperliquidNormalization(unittest.TestCase):
    def test_parse_response_normalizes_hourly_funding_to_eight_hours(self):
        response = [
            {"universe": [{"name": "BTC"}]},
            [{
                "markPx": "100000",
                "dayNtlVlm": "1000000",
                "openInterest": "100",
                "funding": "0.0000125",
                "impactPxs": ["99999", "100001"],
            }],
        ]

        result = HyperliquidCollector().parse_response(response)

        self.assertEqual(result["BTC"]["funding_rate"], Decimal("0.0001"))


if __name__ == "__main__":
    unittest.main()
