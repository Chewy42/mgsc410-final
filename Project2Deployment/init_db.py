import sqlite3
from pathlib import Path

def init_db():
    """Initialize the database with the required schema"""
    db_path = Path(__file__).parent / "amazon_reviews.db"
    
    # SQL to create tables
    create_tables_sql = """
    -- Products table
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,
        description TEXT,
        price REAL
    );

    -- Reviews table
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        user_id TEXT,
        review_summary TEXT,
        review_rating REAL,
        review_text TEXT,
        review_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    -- Create indices for better performance
    CREATE INDEX IF NOT EXISTS idx_product_title ON products(title);
    CREATE INDEX IF NOT EXISTS idx_product_category ON products(category);
    CREATE INDEX IF NOT EXISTS idx_review_product ON reviews(product_id);
    CREATE INDEX IF NOT EXISTS idx_review_rating ON reviews(review_rating);
    """

    try:
        # Connect to database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables and indices
        cursor.executescript(create_tables_sql)
        
        # Insert some sample data if the products table is empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            sample_data_sql = """
            INSERT INTO products (title, category, description, price) VALUES
                ('Wireless Headphones', 'Electronics', 'High-quality wireless headphones with noise cancellation', 99.99),
                ('Python Programming Book', 'Books', 'Comprehensive guide to Python programming', 49.99),
                ('Smart Watch', 'Electronics', 'Fitness tracking smartwatch with heart rate monitor', 199.99);

            INSERT INTO reviews (product_id, user_id, review_summary, review_rating, review_text) VALUES
                (1, 'user123', 'Great sound quality', 4.5, 'These headphones have amazing sound quality and battery life.'),
                (1, 'user456', 'Comfortable fit', 4.0, 'Very comfortable for long listening sessions.'),
                (2, 'user789', 'Excellent resource', 5.0, 'This book helped me learn Python quickly.'),
                (3, 'user321', 'Good features', 4.0, 'Nice smartwatch with many useful features.');
            """
            cursor.executescript(sample_data_sql)

        conn.commit()
        print("Database initialized successfully!")
        
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
