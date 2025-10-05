#!/bin/bash
set -e

# Create test database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE cv_ai_test_db;
    GRANT ALL PRIVILEGES ON DATABASE cv_ai_test_db TO $POSTGRES_USER;
EOSQL

echo "Test database created successfully!"
