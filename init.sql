-- Create the market_data table
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8),
    volume_24h DECIMAL(20, 8),
    open_interest DECIMAL(20, 8),
    funding_rate DECIMAL(10, 8),
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8)
);

-- Create an index for faster queries
CREATE INDEX IF NOT EXISTS idx_exchange_symbol_time 
ON market_data (exchange, symbol, time DESC);

-- If using TimescaleDB, convert to hypertable (optional for now)
-- SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);