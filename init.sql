-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS smartshop_db;

-- Create user if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'smartshop') THEN
      CREATE USER smartshop WITH PASSWORD :'POSTGRES_PASSWORD';
   END IF;
END
$$;

-- Grant specific privileges
GRANT CONNECT ON DATABASE smartshop_db TO smartshop;
GRANT USAGE ON SCHEMA public TO smartshop;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO smartshop;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO smartshop;

-- Connect to the database
\c smartshop_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_products_name_category ON products(name, category);
CREATE INDEX IF NOT EXISTS idx_receipts_user_date ON receipts(user_id, purchase_date);
CREATE INDEX IF NOT EXISTS idx_shopping_lists_user_active ON shopping_lists(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt_product ON receipt_items(receipt_id, product_id);
CREATE INDEX IF NOT EXISTS idx_shopping_list_items_list_product ON shopping_list_items(shopping_list_id, product_id);