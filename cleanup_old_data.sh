#!/bin/bash
set -euo pipefail

docker exec crypto_db psql \
  --username postgres \
  --dbname market_data \
  --set ON_ERROR_STOP=1 \
  --command "DELETE FROM market_data WHERE time < NOW() - INTERVAL '3 days';"
