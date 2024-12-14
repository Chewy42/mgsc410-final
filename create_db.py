import pandas as pd
import sqlite3
from pathlib import Path
import os
import numpy as np
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_chunk(chunk):
    """Process a chunk of data with basic cleaning"""
    chunk = chunk.copy()
    
    # Clean text fields
    text_columns = ['title', 'category', 'description', 'review_summary', 'review_text']
    for col in text_columns:
        chunk[col] = chunk[col].fillna('').astype(str).str.strip()
    
    # Clean numeric fields
    chunk['price'] = pd.to_numeric(chunk['price'], errors='coerce')
    chunk['review_rating'] = pd.to_numeric(chunk['review_rating'], errors='coerce')
    
    # Convert timestamps
    chunk['review_timestamp'] = pd.to_datetime(chunk['review_timestamp'])
    
    return chunk

def create_db():
    """Create and initialize the database with product and review data"""
    try:
        logger.info("Starting database creation")
        db_path = Path(__file__).parent / "amazon_reviews.db"
        csv_path = Path(__file__).parent / "cleaned_purchase_history.csv"
        
        # Create database connection with optimized settings
        conn = sqlite3.connect(str(db_path), isolation_level=None)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent access
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA cache_size=-2000000')  # Use 2GB cache
        cursor.execute('PRAGMA temp_store=MEMORY')
        
        # Create tables with optimized schema
        cursor.execute('''DROP TABLE IF EXISTS products''')
        cursor.execute('''DROP TABLE IF EXISTS reviews''')
        cursor.execute('''DROP TABLE IF EXISTS temp_products''')
        
        # Create a temporary table for products
        cursor.execute('''
        CREATE TABLE temp_products (
            title TEXT PRIMARY KEY,
            category TEXT,
            description TEXT,
            price REAL
        )''')
        
        cursor.execute('''
        CREATE TABLE products (
            title TEXT PRIMARY KEY,
            category TEXT,
            description TEXT,
            price REAL,
            review_count INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0
        )''')
        
        cursor.execute('''
        CREATE TABLE reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            user_id TEXT,
            review_summary TEXT,
            review_rating REAL,
            review_text TEXT,
            review_timestamp TIMESTAMP,
            FOREIGN KEY (title) REFERENCES products(title)
        )''')
        
        # Process data in chunks to manage memory
        chunk_size = 50000
        total_rows = sum(1 for _ in open(csv_path, 'r', encoding='utf-8')) - 1  # subtract header
        total_chunks = (total_rows + chunk_size - 1) // chunk_size
        
        logger.info(f"Processing {total_rows:,} rows in chunks of {chunk_size:,}")
        
        # First pass: collect unique products
        logger.info("First pass: Collecting unique products...")
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size), 1):
            logger.info(f"Processing products from chunk {i}/{total_chunks}")
            chunk = process_chunk(chunk)
            
            # Insert products into temporary table
            products_data = chunk[['title', 'category', 'description', 'price']].drop_duplicates('title', keep='first')
            
            # Insert products in smaller batches
            batch_size = 500
            for start_idx in range(0, len(products_data), batch_size):
                end_idx = min(start_idx + batch_size, len(products_data))
                batch = products_data.iloc[start_idx:end_idx]
                try:
                    batch.to_sql('temp_products', conn, if_exists='append', index=False, method='multi')
                except sqlite3.IntegrityError:
                    # Handle duplicates by inserting one by one
                    for _, row in batch.iterrows():
                        try:
                            cursor.execute('''
                            INSERT OR IGNORE INTO temp_products (title, category, description, price)
                            VALUES (?, ?, ?, ?)
                            ''', (row['title'], row['category'], row['description'], row['price']))
                        except Exception as e:
                            logger.warning(f"Failed to insert product {row['title']}: {str(e)}")
            
            conn.commit()
        
        # Move unique products to final table
        logger.info("Moving unique products to final table...")
        cursor.execute('''
        INSERT INTO products (title, category, description, price)
        SELECT title, category, description, MIN(price) as price
        FROM temp_products
        GROUP BY title, category, description
        ''')
        
        # Drop temporary table
        cursor.execute('DROP TABLE temp_products')
        
        # Second pass: process reviews
        logger.info("Second pass: Processing reviews...")
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size), 1):
            logger.info(f"Processing reviews from chunk {i}/{total_chunks}")
            chunk = process_chunk(chunk)
            
            # Insert reviews in batches
            reviews_data = chunk[[
                'title', 'user_id', 'review_summary', 'review_rating',
                'review_text', 'review_timestamp'
            ]]
            
            # Insert reviews in smaller batches
            batch_size = 10000
            for start_idx in range(0, len(reviews_data), batch_size):
                end_idx = min(start_idx + batch_size, len(reviews_data))
                batch = reviews_data.iloc[start_idx:end_idx]
                batch.to_sql('reviews', conn, if_exists='append', index=False, method='multi')
            
            conn.commit()
            logger.info(f"Completed chunk {i}/{total_chunks}")
        
        # Calculate and update product metrics
        logger.info("Calculating product metrics...")
        cursor.execute('''
        UPDATE products 
        SET review_count = (
            SELECT COUNT(*) 
            FROM reviews 
            WHERE reviews.title = products.title
        ),
        avg_rating = (
            SELECT AVG(review_rating) 
            FROM reviews 
            WHERE reviews.title = products.title
        )
        ''')
        
        # Create indices for better query performance
        logger.info("Creating indices...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_review_title ON reviews(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_review_rating ON reviews(review_rating)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_rating ON products(avg_rating DESC)')
        
        conn.commit()
        logger.info("Database creation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_db()