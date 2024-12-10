from shiny import App, render, ui, reactive
import pandas as pd
import sqlite3
from pathlib import Path
import numpy as np
from functools import lru_cache
from datetime import datetime, timedelta
import logging
import time
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import mmap
import pickle
import hashlib
from functools import lru_cache
import numpy as np
from typing import Dict, List, Tuple, Optional
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TIMEOUT = 300  # 5 minutes cache timeout
ITEMS_PER_PAGE = 25

# Constants for optimization
MAX_WORKERS = 4
CACHE_SIZE = 1000
PRELOAD_PAGES = 3  # Number of adjacent pages to preload
CACHE_FILE = "cache.mmap"
CACHE_SIZE_BYTES = 1024 * 1024 * 100  # 100MB cache

class AdvancedQueryCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._sorted_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._preloaded_data: Dict[str, pd.DataFrame] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._initialize_mmap_cache()
        
    def _initialize_mmap_cache(self):
        try:
            with open(CACHE_FILE, 'r+b') as f:
                self._mmap = mmap.mmap(f.fileno(), CACHE_SIZE_BYTES)
        except:
            with open(CACHE_FILE, 'wb') as f:
                f.write(b'\0' * CACHE_SIZE_BYTES)
            with open(CACHE_FILE, 'r+b') as f:
                self._mmap = mmap.mmap(f.fileno(), CACHE_SIZE_BYTES)
    
    def _get_cache_key_hash(self, key: str) -> bytes:
        return hashlib.sha256(key.encode()).digest()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            # Try memory cache first
            if key in self._cache:
                timestamp = self._timestamps[key]
                if time.time() - timestamp <= CACHE_TIMEOUT:
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
            
            # Try mmap cache
            key_hash = self._get_cache_key_hash(key)
            try:
                self._mmap.seek(0)
                cache_data = pickle.loads(self._mmap.read())
                if key_hash in cache_data:
                    data, timestamp = cache_data[key_hash]
                    if time.time() - timestamp <= CACHE_TIMEOUT:
                        self._cache[key] = data  # Update memory cache
                        self._timestamps[key] = timestamp
                        return data
            except:
                pass
            
            return None
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()
            
            # Update mmap cache
            key_hash = self._get_cache_key_hash(key)
            try:
                self._mmap.seek(0)
                try:
                    cache_data = pickle.loads(self._mmap.read())
                except:
                    cache_data = {}
                
                cache_data[key_hash] = (value, time.time())
                
                # Implement LRU for mmap cache
                if len(cache_data) > CACHE_SIZE:
                    oldest_key = min(cache_data.keys(), key=lambda k: cache_data[k][1])
                    del cache_data[oldest_key]
                
                self._mmap.seek(0)
                self._mmap.write(pickle.dumps(cache_data))
            except Exception as e:
                logger.error(f"Error writing to mmap cache: {e}")
    
    def preload_adjacent_pages(self, base_key: str, current_page: int, sort_column: str, sort_direction: str):
        """Preload adjacent pages in parallel"""
        try:
            # Check if we already have the sorted data
            cached_data = self.get_sorted(base_key, sort_column, sort_direction)
            if cached_data is None or cached_data.empty:
                return  # No data to preload

            # Preload previous and next pages
            pages_to_preload = [p for p in range(current_page - 3, current_page + 4) if p > 0]
            for page in pages_to_preload:
                if page != current_page:
                    self._executor.submit(
                        self._preload_page,
                        base_key,
                        page,
                        sort_column,
                        sort_direction
                    )
        except Exception as e:
            print(f"Error in preload_adjacent_pages: {e}")

    def _preload_page(self, base_key: str, page: int, sort_column: str, sort_direction: str):
        """Worker function for preloading a specific page"""
        try:
            # Extract search terms and categories from base_key
            parts = base_key.split('_')
            search_term = parts[1] if len(parts) > 1 else None
            categories = eval(parts[2]) if len(parts) > 2 else None
            
            df = get_filtered_products_internal(
                search_term=search_term,
                categories=categories,
                page=page,
                sort_column=sort_column,
                sort_direction=sort_direction
            )
            
            cache_key = f"{base_key}_{page}"
            self.set_sorted(cache_key, sort_column, sort_direction, df)
        except Exception as e:
            logger.error(f"Error preloading page {page}: {e}")

    def get_sorted(self, base_key: str, sort_column: str, sort_direction: str) -> Optional[pd.DataFrame]:
        """Get sorted data from cache"""
        try:
            with self._lock:
                if base_key not in self._sorted_cache:
                    return None
                if sort_column not in self._sorted_cache[base_key]:
                    return None
                if sort_direction not in self._sorted_cache[base_key][sort_column]:
                    return None
                return self._sorted_cache[base_key][sort_column][sort_direction]
        except Exception as e:
            print(f"Error in get_sorted: {e}")
            return None
    
    def set_sorted(self, base_key: str, sort_column: str, sort_direction: str, df: pd.DataFrame) -> None:
        with self._lock:
            if base_key not in self._sorted_cache:
                self._sorted_cache[base_key] = {}
            if sort_column not in self._sorted_cache[base_key]:
                self._sorted_cache[base_key][sort_column] = {}
            self._sorted_cache[base_key][sort_column][sort_direction] = df
            self._timestamps[f"{base_key}_{sort_column}_{sort_direction}"] = time.time()

query_cache = AdvancedQueryCache()

@lru_cache(maxsize=1000)
def get_filtered_products_internal(search_term=None, categories=None, page=1, sort_column="Product Score", sort_direction="desc"):
    """Internal function for getting filtered products with caching"""
    sort_column_map = {
        "Product Title": "title",
        "Category": "category",
        "Price": "price",
        "Rating": "avg_rating",
        "Reviews": "review_count",
        "Price vs Category Avg %": "price_diff_percentage",
        "Sentiment Score": "sentiment_per_review",
        "Product Score": "product_score"
    }

    sql_sort_column = sort_column_map.get(sort_column, "product_score") if sort_column and sort_direction != 'none' else None
    sql_sort_direction = "ASC" if sort_direction == "asc" else "DESC" if sort_direction == "desc" else ""
    
    query = """
        SELECT 
            product_id,
            title as "Product Title",
            category as "Category",
            price as "Price",
            ROUND(avg_rating, 1) as "Rating",
            review_count as "Reviews",
            price_diff_percentage as "Price vs Category Avg %",
            sentiment_per_review as "Sentiment Score",
            product_score as "Product Score"
        FROM product_metrics_mv
        WHERE 1=1
    """
    
    params = []
    
    if search_term:
        query += " AND (title LIKE ? OR category LIKE ?)"
        search_pattern = f"%{search_term}%"
        params.extend([search_pattern, search_pattern])
        
    if categories:
        placeholders = " OR ".join(["category LIKE ?" for _ in categories])
        query += f" AND ({placeholders})"
        params.extend([f"%{cat}%" for cat in categories])
    
    if sql_sort_column:
        query += f" ORDER BY {sql_sort_column} {sql_sort_direction}"
    
    query += " LIMIT ? OFFSET ?"
    
    offset = (page - 1) * ITEMS_PER_PAGE
    params.extend([ITEMS_PER_PAGE, offset])
    
    return execute_query(query, tuple(params) if params else None)

def get_filtered_products(search_term=None, categories=None, page=1, sort_column="Product Score", sort_direction="desc"):
    """Get filtered products with advanced caching and preloading"""
    # Generate cache key
    cache_key = f"products_{search_term}_{str(categories)}_{page}"
    
    # Try to get from cache
    if sort_column and sort_direction != 'none':
        cached_df = query_cache.get_sorted(cache_key, sort_column, sort_direction)
        if cached_df is not None:
            # Preload adjacent pages in background
            query_cache.preload_adjacent_pages(f"products_{search_term}_{str(categories)}", page, sort_column, sort_direction)
            return cached_df
    
    # Get data using internal function
    df = get_filtered_products_internal(search_term, categories, page, sort_column, sort_direction)
    
    # Cache the results
    if sort_column and sort_direction != 'none':
        query_cache.set_sorted(cache_key, sort_column, sort_direction, df)
        
    # Preload adjacent pages in background
    query_cache.preload_adjacent_pages(f"products_{search_term}_{str(categories)}", page, sort_column, sort_direction)
    
    return df

def get_db_connection():
    """Get database connection with optimized settings"""
    db_path = Path(__file__).parent / "amazon_reviews.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=-2000000')
    return conn

def execute_query(query: str, params: Optional[tuple] = None, cache: bool = True) -> pd.DataFrame:
    """Execute SQL query with caching and error handling"""
    cache_key = f"{query}_{str(params)}" if params else query
    
    if cache:
        cached_result = query_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query[:100]}...")
            return cached_result
    
    try:
        conn = get_db_connection()
        start_time = time.time()
        
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        
        query_time = time.time() - start_time
        logger.info(f"Query executed in {query_time:.2f} seconds: {query[:100]}...")
        
        if cache:
            query_cache.set(cache_key, df)
        
        return df
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()

def initialize_database():
    """Initialize database with optimized indexes and views"""
    conn = get_db_connection()
    try:
        # Create indexes for frequently accessed columns
        conn.execute('CREATE INDEX IF NOT EXISTS idx_product_title ON products(title);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_product_category ON products(category);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_product_price ON products(price);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_review_rating ON reviews(review_rating);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_review_timestamp ON reviews(review_timestamp);')
        
        # Create materialized view for product metrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_metrics_mv AS
            WITH product_metrics AS (
                SELECT 
                    p.product_id,
                    p.title,
                    p.category,
                    p.price,
                    COUNT(r.review_id) as review_count,
                    AVG(r.review_rating) as avg_rating,
                    SUM(CASE 
                        WHEN r.review_rating >= 4 THEN 2
                        WHEN r.review_rating > 2 THEN 1
                        ELSE -1
                    END) as sentiment_score,
                    SUM(CASE 
                        WHEN julianday('now') - julianday(r.review_timestamp) <= 30 
                        THEN 1 ELSE 0 
                    END) as recent_reviews,
                    AVG(p.price) OVER (PARTITION BY p.category) as avg_category_price,
                    ROUND((p.price - AVG(p.price) OVER (PARTITION BY p.category)) * 100.0 / 
                        NULLIF(AVG(p.price) OVER (PARTITION BY p.category), 0), 1) as price_diff_percentage,
                    ROUND(CAST(SUM(CASE 
                        WHEN r.review_rating >= 4 THEN 2
                        WHEN r.review_rating > 2 THEN 1
                        ELSE -1
                    END) AS FLOAT) / NULLIF(COUNT(r.review_id), 0), 2) as sentiment_per_review,
                    ROUND(
                        (COALESCE(AVG(r.review_rating), 0) * 0.3 + 
                        COALESCE(CAST(SUM(CASE 
                            WHEN julianday('now') - julianday(r.review_timestamp) <= 30 
                            THEN 1 ELSE 0 
                        END) AS FLOAT) / NULLIF(COUNT(r.review_id), 0), 0) * 0.3 +
                        CASE WHEN p.price < AVG(p.price) OVER (PARTITION BY p.category) THEN 0.2 ELSE -0.2 END +
                        COALESCE(CAST(SUM(CASE 
                            WHEN r.review_rating >= 4 THEN 2
                            WHEN r.review_rating > 2 THEN 1
                            ELSE -1
                        END) AS FLOAT) / NULLIF(COUNT(r.review_id), 0), 0) * 0.2) * 100,
                        1
                    ) as product_score
                FROM products p
                LEFT JOIN reviews r ON p.product_id = r.product_id
                GROUP BY p.product_id, p.title, p.category, p.price
            )
            SELECT * FROM product_metrics;
        """)
        
        # Create indexes on materialized view
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mv_title ON product_metrics_mv(title);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mv_category ON product_metrics_mv(category);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mv_price ON product_metrics_mv(price);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mv_product_score ON product_metrics_mv(product_score);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mv_sentiment_score ON product_metrics_mv(sentiment_per_review);')
        
        conn.commit()
    finally:
        conn.close()

# UI Components
def create_filter_input():
    """Enhanced filter input with Material Design and performance optimizations"""
    return ui.div(
        {"class": "filter-section md-elevation-1"},
        ui.div(
            {"class": "filter-wrapper"},
            ui.tags.i({"class": "material-icons filter-icon"}, "filter_list"),
            ui.input_text(
                "category_filter",
                "",
                placeholder="Filter by category...",
            ),
            ui.input_action_button(
                "filter_button",
                "Filter",
                class_="filter-btn"
            )
        )
    )

app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.link(rel="stylesheet", href="styles.css"),
        ui.tags.link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"),
        ui.tags.link(rel="stylesheet", href="https://fonts.googleapis.com/icon?family=Material+Icons"),
        ui.tags.style("""
            /* Base container styles */
            .app-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 24px;
                display: flex;
                flex-direction: column;
                gap: 24px;
            }
            
            /* Header styles */
            .header {
                background: #2196F3;
                color: white;
                padding: 24px;
                border-radius: 8px;
                width: 100%;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .header-title {
                margin: 0;
                font-size: 24px;
                font-weight: 500;
            }
            
            /* Content sections */
            .content-section {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 24px;
                width: 100%;
            }
            
            /* Search section */
            .search-section {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            .search-title {
                margin: 0;
                font-size: 20px;
                color: #1976D2;
            }
            .search-subtitle {
                margin: 0;
                color: #666;
                font-size: 14px;
            }
            .search-form {
                display: flex;
                gap: 16px;
                align-items: center;
            }
            .input-wrapper {
                flex: 1;
            }
            .input-wrapper input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            .search-button {
                padding: 12px 24px;
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                white-space: nowrap;
            }
            .search-button:hover {
                background: #1976D2;
            }
            
            /* Table section */
            .table-section {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            .table-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .table-title {
                margin: 0;
                font-size: 20px;
                color: #1976D2;
            }
            
            /* Filter section */
            .filter-wrapper {
                min-width: 250px;
                max-width: 300px;
            }
            .selectize-input {
                padding: 12px;
                font-size: 14px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            
            /* Table styles */
            .products-table {
                width: 100%;
                margin-top: 16px;
            }
            .products-table table {
                width: 100%;
                border-collapse: collapse;
            }
            .products-table th, .products-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            .products-table th {
                background: #f5f5f5;
                font-weight: 500;
            }
            
            /* Column widths */
            .products-table th:nth-child(1) { width: 25%; } /* Product Title */
            .products-table th:nth-child(2) { width: 15%; } /* Category */
            .products-table th:nth-child(3) { width: 10%; } /* Price */
            .products-table th:nth-child(4) { width: 10%; } /* Rating */
            .products-table th:nth-child(5) { width: 10%; } /* Reviews */
            .products-table th:nth-child(6) { width: 10%; } /* Price vs Category */
            .products-table th:nth-child(7) { width: 10%; } /* Sentiment Score */
            .products-table th:nth-child(8) { width: 10%; } /* Product Score */
            
            .products-table {
                max-height: 600px;
                overflow-y: auto;
            }
            .products-table thead {
                position: sticky;
                top: 0;
                background: white;
                z-index: 1;
            }
            .products-table td {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            .rating.positive { color: #28a745; }
            .rating.negative { color: #dc3545; }
            .rating.neutral { color: #dc3545; }
            .product-row { cursor: pointer; }
            .product-row:hover { background-color: #f8f9fa; }
            
            /* Hide sort inputs */
            #sort_column, #sort_direction {
                position: absolute;
                left: -9999px;
            }
            
            /* Modal styles */
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.4);
            }
            .modal-content {
                background-color: #fefefe;
                margin: 15% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 80%;
                max-width: 800px;
                max-height: 70vh;
                overflow-y: auto;
                border-radius: 8px;
                position: relative;
            }
            .close-modal {
                position: absolute;
                right: 20px;
                top: 10px;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .close-modal:hover {
                color: #666;
            }
            .review-item {
                border-bottom: 1px solid #eee;
                padding: 10px 0;
            }
            .review-rating {
                font-weight: bold;
                margin-right: 10px;
            }
            .review-date {
                color: #666;
                font-size: 0.9em;
            }
        """)
    ),
    ui.div(
        {"class": "app-container"},
        # Sort inputs (hidden)
        ui.input_text("sort_column", label="", value="Product Score"),
        ui.input_text("sort_direction", label="", value="desc"),
        # Header
        ui.div(
            {"class": "header"},
            ui.tags.i({"class": "material-icons"}, "trending_up"),
            ui.h1({"class": "header-title"}, "Amazon Emerging Products Finder")
        ),
        # Search Section
        ui.div(
            {"class": "content-section search-section"},
            ui.h2({"class": "search-title"}, "Discover Products"),
            ui.p({"class": "search-subtitle"}, "Find emerging products and analyze their performance"),
            ui.div(
                {"class": "search-form"},
                ui.div(
                    {"class": "input-wrapper"},
                    ui.input_text(
                        "product_search",
                        "",
                        placeholder="Enter product name or category..."
                    )
                ),
                ui.input_action_button(
                    "refresh_search",
                    "Search",
                    class_="search-button"
                )
            )
        ),
        # Table Section
        ui.div(
            {"class": "content-section table-section"},
            ui.div(
                {"class": "table-header"},
                ui.h2({"class": "table-title"}, "Product List"),
                create_filter_input()
            ),
            ui.div(
                {"class": "table-content"},
                ui.output_ui("products_table", class_="products-table"),
                ui.div(
                    {"id": "reviewsModal", "class": "modal"},
                    ui.div(
                        {"class": "modal-content"},
                        ui.span({"class": "close-modal", "onclick": "closeModal()"}, "×"),
                        ui.h2("Product Reviews"),
                        ui.output_ui("reviews_content")
                    )
                )
            )
        )
    ),
    # Load script.js at the end of body
    ui.tags.script(src="script.js"),
    # Add debug script
    ui.tags.script("""
        console.log('Page loaded');
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded');
            console.log('Sort inputs:', {
                column: document.querySelector('#sort_column'),
                direction: document.querySelector('#sort_direction')
            });
            console.log('Sortable headers:', document.querySelectorAll('th.sortable').length);
        });
    """)
)

def server(input, output, session):
    # Create reactive values
    products_data = reactive.Value(pd.DataFrame())
    current_page = reactive.Value(1)
    
    # Update products when search or filters change
    @reactive.Effect
    @reactive.event(input.product_search, input.filter_button, input.sort_column, input.sort_direction)
    def _():
        current_page.set(1)  # Reset to first page
        # Split the filter input by commas to handle multiple categories
        categories = [cat.strip() for cat in input.category_filter().split(',')] if input.category_filter() else None
        products_df = get_filtered_products(
            search_term=input.product_search(),
            categories=categories,
            page=current_page.get(),
            sort_column=input.sort_column(),
            sort_direction=input.sort_direction()
        )
        products_data.set(products_df)
    
    # Store unique categories
    @reactive.Effect
    def _():
        df = execute_query("""
            SELECT DISTINCT
                TRIM(category) as category
            FROM products
            WHERE category IS NOT NULL
                AND LENGTH(category) > 1
            ORDER BY category;
        """)
        # ui.update_selectize(
        #     "category_filter",
        #     choices=df['category'].tolist(),
        #     selected=[]
        # )

    @output
    @render.ui
    def products_table():
        try:
            df = products_data.get()
            if df.empty:
                return ui.div(
                    {"class": "table-empty"},
                    ui.tags.i({"class": "fas fa-box-open", "style": "font-size: 48px; margin-bottom: 16px;"}),
                    ui.tags.h3("No Products Found"),
                    ui.tags.p("Try adjusting your search criteria or filters")
                )
            
            # Create table header with sort indicators
            columns = [
                ("Product Title", "Product Title"),
                ("Category", "Category"),
                ("Price", "Price"),
                ("Rating", "Rating"),
                ("Reviews", "Reviews"),
                ("Price vs Category Avg %", "Price vs Category Avg %"),
                ("Sentiment Score", "Sentiment Score"),
                ("Product Score", "Product Score")
            ]

            header = ui.tags.thead(
                ui.tags.tr([
                    ui.tags.th(
                        {
                            "class": f"sortable {input.sort_direction() if col[0] == input.sort_column() else ''}", 
                            "data-column": col[0],
                            "style": """
                                cursor: pointer;
                                position: relative;
                                padding-right: 20px;
                            """,
                            "role": "button",
                            "tabindex": "0"
                        },
                        [
                            col[1],
                            ui.tags.span(
                                {
                                    "class": f"sort-indicator {'active' if col[0] == input.sort_column() else ''}",
                                    "style": f"""
                                        position: absolute;
                                        right: 5px;
                                        top: 50%;
                                        transform: translateY(-50%);
                                        {'content: "↑"' if col[0] == input.sort_column() and input.sort_direction() == 'asc' else 'content: "↓"' if col[0] == input.sort_column() else ''}
                                    """
                                },
                                "↑" if col[0] == input.sort_column() and input.sort_direction() == 'asc' else "↓" if col[0] == input.sort_column() else ""
                            )
                        ]
                    ) for col in columns
                ])
            )

            # Create table rows with improved interactivity
            rows = []
            for _, row in df.iterrows():
                rows.append(
                    ui.tags.tr(
                        {
                            "class": "product-row",
                            "onclick": f"showReviews('{row['product_id']}')",
                            "role": "button",
                            "tabindex": "0"
                        }, [
                            ui.tags.td(row["Product Title"]),
                            ui.tags.td(row["Category"]),
                            ui.tags.td(row["Price"]),
                            ui.tags.td(row["Rating"]),
                            ui.tags.td(row["Reviews"]),
                            ui.tags.td(row["Price vs Category Avg %"]),
                            ui.tags.td(row["Sentiment Score"]),
                            ui.tags.td(row["Product Score"])
                        ]
                    )
                )

            # Create table body
            body = ui.tags.tbody(rows)

            # Return complete table with loading state
            return ui.div(
                {"class": "table-container"},
                ui.tags.div(
                    {"class": "table-loading", "id": "table-loading", "style": "display: none;"},
                    ui.tags.div({"class": "spinner-border text-primary"})
                ),
                ui.tags.table(
                    {"class": "products-table"},
                    [header, body]
                )
            )
        except Exception as e:
            logger.error(f"Error rendering table: {str(e)}")
            return ui.div(
                {"class": "table-empty error"},
                ui.tags.i({"class": "fas fa-exclamation-circle", "style": "font-size: 48px; margin-bottom: 16px; color: #C62828;"}),
                ui.tags.h3("Error Loading Products"),
                ui.tags.p(str(e))
            )

    @output
    @render.ui
    def reviews_content():
        product_id = input.selected_product()
        if not product_id:
            return None
            
        query = """
            SELECT 
                r.review_rating,
                r.review_text,
                r.review_timestamp,
                p.title as product_title
            FROM reviews r
            JOIN products p ON r.product_id = p.product_id
            WHERE r.product_id = ?
            ORDER BY r.review_timestamp DESC
        """
        
        df = execute_query(query, (product_id,))
        if df.empty:
            return ui.p("No reviews found for this product.")
            
        reviews = []
        product_title = df.iloc[0]['product_title']
        reviews.append(ui.h3(product_title))
        
        for _, review in df.iterrows():
            rating_class = "positive" if review['review_rating'] == 5.0 else "negative"
            reviews.append(
                ui.div(
                    {"class": "review-item"},
                    ui.span(
                        f"{review['review_rating']}★",
                        {"class": f"review-rating rating {rating_class}"}
                    ),
                    ui.span(
                        review['review_timestamp'],
                        {"class": "review-date"}
                    ),
                    ui.p(review['review_text'])
                )
            )
            
        return ui.div(reviews)

if __name__ == "__main__":
    initialize_database()
    app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
    app.run(host="localhost", port=5000)