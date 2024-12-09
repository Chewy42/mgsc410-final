import sqlite3
from pathlib import Path

def check_data():
    db_path = Path(__file__).parent / "amazon_reviews.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if there's data in the products table
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    print(f"Total number of products: {count}")
    
    # Check first few rows of category column
    cursor.execute("SELECT category FROM products LIMIT 5")
    categories = cursor.fetchall()
    print("\nFirst 5 categories:")
    for cat in categories:
        print(cat[0])
    
    conn.close()

if __name__ == "__main__":
    check_data()
