import sqlite3
from pathlib import Path

def get_table_info():
    db_path = Path(__file__).parent / "amazon_reviews.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(products)")
    columns = cursor.fetchall()
    
    print("Products table columns:")
    for col in columns:
        print(f"Column: {col[1]}, Type: {col[2]}")
    
    conn.close()

if __name__ == "__main__":
    get_table_info()
