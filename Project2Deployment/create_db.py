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

def calculate_product_metrics(df_group):
    """Calculate product metrics for a group of reviews"""
    now = datetime.now()
    metrics = {
        'review_count': len(df_group),
        'avg_rating': df_group['review_rating'].mean(),
        'sentiment_score': sum(
            2 if rating >= 4 else (1 if rating > 2 else -1)
            for rating in df_group['review_rating']
        ),
        'recent_reviews': sum(
            1 for timestamp in pd.to_datetime(df_group['review_timestamp'])
            if (now - timestamp).days <= 30
        )
    }
    return pd.Series(metrics)

def process_chunk(chunk, min_price=1.0):
    """Process a chunk of data with basic cleaning and filtering"""
    chunk = chunk.copy()
    
    # Remove products with invalid prices
    chunk = chunk[chunk['price'].notna()]
    chunk = chunk[chunk['price'] > min_price]
    
    # Clean text fields and ensure they exist
    required_columns = ['title', 'category', 'description', 'review_text', 'review_summary']
    for col in required_columns:
        if col not in chunk.columns:
            chunk[col] = ''
        else:
            chunk[col] = chunk[col].fillna('')
            chunk[col] = chunk[col].astype(str).str.strip()
    
    # Convert timestamps
    chunk['review_timestamp'] = pd.to_datetime(chunk['review_timestamp'])
    
    return chunk

def create_db(csv_file, chunk_size=50000):
    """Create and initialize the database with product and review data"""
    try:
        logger.info(f"Starting database creation from: {csv_file}")
        db_path = Path(__file__).parent / "amazon_reviews.db"
        
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
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            description TEXT,
            price REAL,
            review_count INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0,
            sentiment_score INTEGER DEFAULT 0,
            recent_reviews INTEGER DEFAULT 0,
            price_competitiveness REAL DEFAULT 0,
            product_score REAL DEFAULT 0
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_id TEXT,
            review_summary TEXT,
            review_rating REAL,
            review_text TEXT,
            review_timestamp TIMESTAMP,
            sentiment_label INTEGER,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )''')
        
        # Create optimized indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_score ON products(product_score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_category ON products(title, category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_category ON products(category, price)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_review_product_time ON reviews(product_id, review_timestamp)')
        
        # Process data in chunks
        chunks = pd.read_csv(csv_file, chunksize=chunk_size)
        all_products = []
        all_reviews = []
        
        logger.info("Processing data chunks...")
        for chunk in chunks:
            # Process chunk
            chunk = process_chunk(chunk)
            
            # Get unique products
            products = chunk[['title', 'category', 'description', 'price']].drop_duplicates()
            all_products.append(products)
            
            # Prepare reviews
            reviews = chunk[['title', 'user_id', 'review_summary', 'review_rating', 'review_text', 'review_timestamp']]
            reviews['sentiment_label'] = reviews['review_rating'].apply(
                lambda x: 2 if x >= 4 else (1 if x > 2 else 0)
            )
            all_reviews.append(reviews)
        
        # Combine all products and calculate metrics
        logger.info("Calculating product metrics...")
        products_df = pd.concat(all_products).drop_duplicates()
        reviews_df = pd.concat(all_reviews)
        
        # Calculate product metrics
        product_metrics = reviews_df.groupby('title').apply(calculate_product_metrics)
        products_df = products_df.join(product_metrics, on='title')
        
        # Calculate price competitiveness
        products_df['price_competitiveness'] = products_df.groupby('category').apply(
            lambda x: (x['price'] - x['price'].mean()) / x['price'].std()
        ).reset_index(level=0, drop=True)
        
        # Calculate final product score
        products_df['product_score'] = (
            products_df['avg_rating'].fillna(0) * 0.3 +
            (products_df['recent_reviews'].fillna(0) / products_df['review_count'].clip(lower=1)) * 0.3 +
            (-products_df['price_competitiveness'].clip(-1, 1) * 0.2) +
            (products_df['sentiment_score'].fillna(0) / products_df['review_count'].clip(lower=1)) * 0.2
        ) * 100
        
        # Fill NaN values
        products_df = products_df.fillna({
            'review_count': 0,
            'avg_rating': 0,
            'sentiment_score': 0,
            'recent_reviews': 0,
            'price_competitiveness': 0,
            'product_score': 0
        })
        
        # Insert data
        logger.info("Inserting processed data into database...")
        
        # Insert products in smaller chunks
        products_columns = ['title', 'category', 'description', 'price', 'review_count', 
                          'avg_rating', 'sentiment_score', 'recent_reviews', 
                          'price_competitiveness', 'product_score']
        for i in range(0, len(products_df), 1000):
            chunk = products_df[products_columns].iloc[i:i+1000]
            chunk.to_sql('products', conn, if_exists='append', index=True, 
                        index_label='product_id', method='multi')
        
        # Get product IDs for reviews
        product_ids = pd.read_sql('SELECT product_id, title FROM products', conn)
        reviews_df = reviews_df.merge(product_ids, on='title')
        
        # Insert reviews in smaller chunks
        reviews_columns = ['product_id', 'user_id', 'review_summary', 'review_rating', 
                         'review_text', 'review_timestamp', 'sentiment_label']
        for i in range(0, len(reviews_df), 1000):
            chunk = reviews_df[reviews_columns].iloc[i:i+1000]
            chunk.to_sql('reviews', conn, if_exists='append', index=True,
                        index_label='review_id', method='multi')
        
        # Final optimizations
        cursor.execute('ANALYZE')
        cursor.execute('VACUUM')
        
        logger.info("Database created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    csv_path = base_dir / "data" / "cleaned_purchase_history.csv"
    create_db(str(csv_path))