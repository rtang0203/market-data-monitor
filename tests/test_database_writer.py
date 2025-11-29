import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from decimal import Decimal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector_hyperliquid import DatabaseWriter


class TestDatabaseWriter(unittest.TestCase):
    """Unit tests for DatabaseWriter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'dbname': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'localhost',
            'port': 5432
        }
        self.db_writer = DatabaseWriter(self.config)

    def tearDown(self):
        """Clean up after tests"""
        if self.db_writer.conn:
            self.db_writer.conn = None

    @patch('collector_hyperliquid.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        self.db_writer.connect()

        mock_connect.assert_called_once_with(**self.config)
        self.assertEqual(self.db_writer.conn, mock_conn)

    @patch('collector_hyperliquid.psycopg2.connect')
    def test_connect_failure(self, mock_connect):
        """Test database connection failure raises exception"""
        mock_connect.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception):
            self.db_writer.connect()

    def test_is_connected_when_no_connection(self):
        """Test is_connected returns False when no connection exists"""
        self.db_writer.conn = None
        self.assertFalse(self.db_writer.is_connected())

    def test_is_connected_when_connected(self):
        """Test is_connected returns True when connection is alive"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        self.db_writer.conn = mock_conn

        result = self.db_writer.is_connected()

        self.assertTrue(result)
        mock_cursor.execute.assert_called_once_with('SELECT 1')
        mock_cursor.close.assert_called_once()

    def test_is_connected_when_connection_dead(self):
        """Test is_connected returns False when connection fails"""
        mock_conn = Mock()
        mock_conn.cursor.side_effect = Exception("Connection lost")

        self.db_writer.conn = mock_conn

        result = self.db_writer.is_connected()

        self.assertFalse(result)

    @patch.object(DatabaseWriter, 'connect')
    @patch.object(DatabaseWriter, 'is_connected')
    def test_ensure_connection_when_connected(self, mock_is_connected, mock_connect):
        """Test ensure_connection does nothing when already connected"""
        mock_is_connected.return_value = True

        self.db_writer.ensure_connection()

        mock_is_connected.assert_called_once()
        mock_connect.assert_not_called()

    @patch.object(DatabaseWriter, 'connect')
    @patch.object(DatabaseWriter, 'is_connected')
    def test_ensure_connection_when_disconnected(self, mock_is_connected, mock_connect):
        """Test ensure_connection reconnects when disconnected"""
        mock_is_connected.return_value = False
        mock_old_conn = Mock()
        self.db_writer.conn = mock_old_conn

        self.db_writer.ensure_connection()

        mock_is_connected.assert_called_once()
        mock_old_conn.close.assert_called_once()
        mock_connect.assert_called_once()

    def test_insert_market_data_batch_empty_list(self):
        """Test batch insert with empty list does nothing"""
        mock_conn = Mock()
        self.db_writer.conn = mock_conn

        self.db_writer.insert_market_data_batch([])

        mock_conn.cursor.assert_not_called()

    def test_insert_market_data_batch_success(self):
        """Test successful batch insert"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        self.db_writer.conn = mock_conn

        # Create test data
        test_time = datetime.now(timezone.utc)
        test_data = [
            {
                'time': test_time,
                'exchange': 'hyperliquid',
                'symbol': 'BTC',
                'price': Decimal('50000.00'),
                'volume_24h': Decimal('1000000.00'),
                'open_interest': Decimal('500000.00'),
                'funding_rate': Decimal('0.0001'),
                'bid': Decimal('49999.00'),
                'ask': Decimal('50001.00')
            },
            {
                'time': test_time,
                'exchange': 'hyperliquid',
                'symbol': 'ETH',
                'price': Decimal('3000.00'),
                'volume_24h': Decimal('500000.00'),
                'open_interest': Decimal('250000.00'),
                'funding_rate': Decimal('0.0002'),
                'bid': Decimal('2999.00'),
                'ask': Decimal('3001.00')
            }
        ]

        self.db_writer.insert_market_data_batch(test_data)

        # Verify cursor operations
        mock_conn.cursor.assert_called_once()
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

        # Verify the SQL query and data structure
        call_args = mock_cursor.executemany.call_args
        query = call_args[0][0]
        batch_data = call_args[0][1]

        self.assertIn('INSERT INTO market_data', query)
        self.assertEqual(len(batch_data), 2)
        self.assertEqual(batch_data[0][2], 'BTC')  # symbol
        self.assertEqual(batch_data[1][2], 'ETH')  # symbol

    def test_insert_market_data_batch_failure(self):
        """Test batch insert handles errors and rolls back"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.executemany.side_effect = Exception("Insert failed")
        mock_conn.cursor.return_value = mock_cursor

        self.db_writer.conn = mock_conn

        test_data = [{
            'time': datetime.now(timezone.utc),
            'exchange': 'hyperliquid',
            'symbol': 'BTC',
            'price': Decimal('50000.00'),
            'volume_24h': Decimal('1000000.00'),
            'open_interest': Decimal('500000.00'),
            'funding_rate': Decimal('0.0001'),
            'bid': Decimal('49999.00'),
            'ask': Decimal('50001.00')
        }]

        with self.assertRaises(Exception):
            self.db_writer.insert_market_data_batch(test_data)

        mock_conn.rollback.assert_called_once()

    def test_close(self):
        """Test closing database connection"""
        mock_conn = Mock()
        self.db_writer.conn = mock_conn

        self.db_writer.close()

        mock_conn.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
