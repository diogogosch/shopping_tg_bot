-- Initial database schema for SmartShopBot

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Purchases table
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    quantity VARCHAR(50),
    unit VARCHAR(20),
    price VARCHAR(20),
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_item_name ON purchases(item_name);
CREATE INDEX IF NOT EXISTS idx_purchases_category ON purchases(category);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchase_date);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);

-- Insert default categories
INSERT INTO categories (name, keywords) VALUES
('produce', ARRAY['apple', 'banana', 'orange', 'tomato', 'lettuce', 'carrot', 'onion', 'potato', 'fruit', 'vegetable', 'avocado', 'spinach', 'broccoli', 'cucumber', 'pepper']),
('dairy', ARRAY['milk', 'cheese', 'yogurt', 'butter', 'cream', 'eggs', 'cottage cheese', 'sour cream', 'mozzarella', 'cheddar']),
('meat', ARRAY['chicken', 'beef', 'pork', 'fish', 'salmon', 'turkey', 'ham', 'bacon', 'sausage', 'lamb', 'shrimp', 'tuna']),
('pantry', ARRAY['rice', 'pasta', 'bread', 'flour', 'sugar', 'salt', 'oil', 'vinegar', 'spice', 'cereal', 'oats', 'quinoa']),
('beverages', ARRAY['water', 'juice', 'soda', 'coffee', 'tea', 'beer', 'wine', 'energy drink', 'smoothie']),
('frozen', ARRAY['ice cream', 'frozen', 'pizza', 'frozen vegetables', 'frozen fruit', 'frozen meals']),
('household', ARRAY['soap', 'detergent', 'toilet paper', 'cleaning', 'shampoo', 'toothpaste', 'deodorant', 'tissues']),
('snacks', ARRAY['chips', 'cookies', 'candy', 'chocolate', 'nuts', 'crackers', 'popcorn', 'granola bar']),
('bakery', ARRAY['bread', 'cake', 'pastry', 'muffin', 'bagel', 'croissant', 'donut', 'pie']),
('other', ARRAY[])
ON CONFLICT (name) DO NOTHING;
