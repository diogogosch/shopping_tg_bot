-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS smartshop_db;

-- Create user if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'smartshop') THEN
      CREATE USER smartshop WITH PASSWORD 'password';
   END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE smartshop_db TO smartshop;

-- Connect to the database
\c smartshop_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO smartshop;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smartshop;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smartshop;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_receipts_user_date ON receipts(user_id, purchase_date);
CREATE INDEX IF NOT EXISTS idx_shopping_lists_user_active ON shopping_lists(user_id, is_active);
