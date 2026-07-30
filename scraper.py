"""
Competitor Price Tracker - Multi-Store Scraper & Time-Series History Engine
---------------------------------------------------------------------------
Demonstrates enterprise data architecture by capturing time-series price snapshots into an
auxiliary SQLite database table ('price_history') during each scraping run. Automatically seeds
historical daily price trend lines across Amazon India, Flipkart, and Reliance Digital.
"""

import os
import re
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Scraper Engine] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

DEFAULT_TARGET_URL = "http://books.toscrape.com/"
CATALOG_PAGE_URL = "http://books.toscrape.com/catalogue/page-{}.html"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =====================================================================
# MODULAR PLUGGABLE STORE ADAPTER ARCHITECTURE
# =====================================================================

class StoreAdapter:
    """Abstract Base Class for modular retail competitor pricing adapters."""
    def __init__(self, store_name: str):
        self.store_name = store_name

    def calculate_price(self, base_price: float, title: str) -> float:
        raise NotImplementedError("Each retail store adapter must implement calculate_price().")


class AmazonIndiaAdapter(StoreAdapter):
    """Simulates Amazon India dynamic algorithm pricing & Prime discount structures."""
    def __init__(self):
        super().__init__("Amazon India")

    def calculate_price(self, base_price: float, title: str) -> float:
        multiplier = random.choice([random.uniform(0.88, 0.96), random.uniform(0.97, 1.03)])
        return round(base_price * multiplier, 2)


class FlipkartAdapter(StoreAdapter):
    """Simulates Flipkart competitive pricing and seasonal sale discounts."""
    def __init__(self):
        super().__init__("Flipkart")

    def calculate_price(self, base_price: float, title: str) -> float:
        multiplier = random.choice([random.uniform(0.86, 0.95), random.uniform(0.98, 1.05)])
        return round(base_price * multiplier, 2)


class RelianceDigitalAdapter(StoreAdapter):
    """Simulates Reliance retail standard competitive retail pricing."""
    def __init__(self):
        super().__init__("Reliance Digital")

    def calculate_price(self, base_price: float, title: str) -> float:
        multiplier = random.uniform(0.91, 1.04)
        return round(base_price * multiplier, 2)


STORE_ADAPTERS = [
    AmazonIndiaAdapter(),
    FlipkartAdapter(),
    RelianceDigitalAdapter()
]

# =====================================================================
# DATABASE SCHEMA & MIGRATION ENGINE (INCLUDING TIME-SERIES HISTORY)
# =====================================================================

def init_db(db_path: str = DB_FILE) -> None:
    """
    Initializes SQLite database and migrates existing tables to store multi-store competitor pricing
    and time-series price historical records.
    """
    logging.info(f"Checking database schema and time-series history tables at: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            # Primary schema with multi-store pricing columns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE NOT NULL,
                    price_str TEXT NOT NULL,
                    price_num REAL NOT NULL,
                    availability TEXT NOT NULL,
                    rating TEXT,
                    last_updated TIMESTAMP NOT NULL,
                    price_delta_str TEXT DEFAULT '',
                    price_direction TEXT DEFAULT 'same',
                    price_amazon REAL DEFAULT 0.0,
                    price_flipkart REAL DEFAULT 0.0,
                    price_reliance REAL DEFAULT 0.0,
                    best_store TEXT DEFAULT 'BooksToScrape',
                    best_price REAL DEFAULT 0.0
                )
            """)
            
            # Auxiliary Time-Series Schema for Historical Price Trend Charts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_title TEXT NOT NULL,
                    store_name TEXT NOT NULL,
                    price_num REAL NOT NULL,
                    snapshot_date DATE NOT NULL,
                    UNIQUE(book_title, store_name, snapshot_date)
                )
            """)
            
            # Auto-Migration Check for older schema versions
            cursor.execute("PRAGMA table_info(books)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            migrations = {
                "price_delta_str": "TEXT DEFAULT ''",
                "price_direction": "TEXT DEFAULT 'same'",
                "price_amazon": "REAL DEFAULT 0.0",
                "price_flipkart": "REAL DEFAULT 0.0",
                "price_reliance": "REAL DEFAULT 0.0",
                "best_store": "TEXT DEFAULT 'BooksToScrape'",
                "best_price": "REAL DEFAULT 0.0"
            }
            
            for col_name, col_def in migrations.items():
                if col_name not in existing_columns:
                    logging.info(f"Migrating database schema: Adding column '{col_name}' to table 'books'...")
                    cursor.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_def};")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price ON books(price_num);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON books(title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_title ON price_history(book_title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_date ON price_history(snapshot_date);")
        logging.info("SQLite time-series and multi-store schema verified successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error during initialization: {e}")
        raise
    finally:
        conn.close()


def fetch_page_html(url: str, timeout: int = 10) -> Optional[str]:
    """Fetches HTML content from target URL with exception protection."""
    try:
        logging.info(f"Sending HTTP GET request to: {url}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    except Exception as e:
        logging.error(f"HTTP network error when requesting {url}: {e}")
        return None


def parse_books_from_html(html_content: str) -> List[Dict[str, Any]]:
    """Parses structural HTML using BeautifulSoup to extract metadata and convert to Indian Rupees (₹)."""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    books_data = []

    for pod in soup.find_all("article", class_="product_pod"):
        try:
            h3_tag = pod.find("h3")
            title = h3_tag.find("a").get("title") if h3_tag and h3_tag.find("a") else "Unknown Title"

            price_tag = pod.find("p", class_="price_color")
            raw_price_str = price_tag.get_text(strip=True) if price_tag else "£0.00"
            price_matches = re.findall(r"[\d.]+", raw_price_str)
            base_price = float(price_matches[0]) if price_matches else 0.0

            inr_rate = 105.0
            price_num = round(base_price * inr_rate, 2)
            clean_price_str = f"₹{price_num:,.2f}"

            avail_tag = pod.find("p", class_="instock availability")
            availability = avail_tag.get_text(strip=True) if avail_tag else "Unknown"

            rating_tag = pod.find("p", class_="star-rating")
            rating = "None"
            if rating_tag and isinstance(rating_tag.get("class"), list):
                classes = [cls for cls in rating_tag.get("class") if cls != "star-rating"]
                rating = classes[0] if classes else "None"

            books_data.append({
                "title": title,
                "price_str": clean_price_str,
                "price_num": price_num,
                "availability": availability,
                "rating": rating,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logging.warning(f"Error parsing individual product element: {e}")
            continue

    return books_data


def save_books_to_db(books_list: List[Dict[str, Any]], db_path: str = DB_FILE, simulate_volatility: bool = True) -> Dict[str, int]:
    """
    Saves scraped books into SQLite, evaluates price volatility deltas, invokes
    pluggable Store Adapters, and logs time-series historical price snapshots.
    """
    if not books_list:
        return {"processed": 0, "new": 0, "price_drops": 0, "price_hikes": 0}

    conn = sqlite3.connect(db_path)
    stats = {"processed": len(books_list), "new": 0, "price_drops": 0, "price_hikes": 0}
    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        with conn:
            cursor = conn.cursor()
            
            for item in books_list:
                title = item["title"]
                new_price_num = item["price_num"]
                
                # Check existing record
                cursor.execute("SELECT id, price_num FROM books WHERE title = ?", (title,))
                existing_row = cursor.fetchone()
                
                price_delta_str = ""
                price_direction = "same"

                if existing_row:
                    old_price_num = float(existing_row[1])
                    if simulate_volatility and random.random() < 0.45:
                        fluctuation = random.choice([random.uniform(-0.14, -0.04), random.uniform(0.03, 0.09)])
                        new_price_num = round(old_price_num * (1.0 + fluctuation), 2)
                        item["price_num"] = new_price_num
                        item["price_str"] = f"₹{new_price_num:,.2f}"

                    delta = round(new_price_num - old_price_num, 2)
                    if abs(delta) >= 1.0:
                        pct_change = abs(delta / old_price_num) * 100
                        if delta < 0:
                            price_direction = "drop"
                            price_delta_str = f"▼ ₹{abs(delta):,.0f} (-{pct_change:.1f}%)"
                            stats["price_drops"] += 1
                        else:
                            price_direction = "hike"
                            price_delta_str = f"▲ ₹{abs(delta):,.0f} (+{pct_change:.1f}%)"
                            stats["price_hikes"] += 1
                else:
                    stats["new"] += 1
                    price_direction = "new"
                    price_delta_str = "NEW ADDITION"

                # Calculate Multi-Store Offers
                store_offers = {"BooksToScrape": new_price_num}
                price_amz = STORE_ADAPTERS[0].calculate_price(new_price_num, title)
                price_flp = STORE_ADAPTERS[1].calculate_price(new_price_num, title)
                price_rel = STORE_ADAPTERS[2].calculate_price(new_price_num, title)
                
                store_offers["Amazon India"] = price_amz
                store_offers["Flipkart"] = price_flp
                store_offers["Reliance Digital"] = price_rel

                best_store, best_price = min(store_offers.items(), key=lambda x: x[1])

                # Upsert primary product table
                upsert_query = """
                    INSERT OR REPLACE INTO books 
                    (title, price_str, price_num, availability, rating, last_updated, 
                     price_delta_str, price_direction, price_amazon, price_flipkart, 
                     price_reliance, best_store, best_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(upsert_query, (
                    title, item["price_str"], new_price_num, item["availability"],
                    item["rating"], item["last_updated"], price_delta_str, price_direction,
                    price_amz, price_flp, price_rel, best_store, best_price
                ))

                # =============================================================
                # TIME-SERIES HISTORICAL PRICE RECORDING
                # =============================================================
                # Check if historical trend line exists for this book title
                cursor.execute("SELECT COUNT(*) FROM price_history WHERE book_title = ?", (title,))
                hist_count = cursor.fetchone()[0]

                # If no previous history exists, seed 7 days of realistic historical competitor trend lines
                if hist_count == 0:
                    for day_offset in range(7, 0, -1):
                        hist_date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                        for st_name, current_p in store_offers.items():
                            # Simulate past volatility variance (-8% to +8%)
                            historical_price = round(current_p * random.uniform(0.92, 1.08), 2)
                            cursor.execute("""
                                INSERT OR IGNORE INTO price_history (book_title, store_name, price_num, snapshot_date)
                                VALUES (?, ?, ?, ?)
                            """, (title, st_name, historical_price, hist_date))

                # Always record or update today's current price snapshot across all 4 platforms!
                for st_name, current_p in store_offers.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO price_history (book_title, store_name, price_num, snapshot_date)
                        VALUES (?, ?, ?, ?)
                    """, (title, st_name, current_p, today_str))

        logging.info(f"Database & historical trend sync complete. New: {stats['new']}, Drops: {stats['price_drops']}, Hikes: {stats['price_hikes']}")
    except sqlite3.Error as e:
        logging.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()

    return stats


def run_scraper(start_page: int = 1, max_pages: int = 2, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Master controller orchestrating catalog harvesting and multi-store trend recording."""
    logging.info(f"Starting Multi-Store & Time-Series Scraper Engine from page {start_page} across {max_pages} pages...")
    init_db(db_path)

    total_harvested_books = []
    end_page = start_page + max_pages
    
    for page_num in range(start_page, end_page):
        url = DEFAULT_TARGET_URL if page_num == 1 else CATALOG_PAGE_URL.format(page_num)
        html_data = fetch_page_html(url)
        if html_data:
            total_harvested_books.extend(parse_books_from_html(html_data))

    save_stats = save_books_to_db(total_harvested_books, db_path, simulate_volatility=True)

    summary = {
        "status": "success" if save_stats["processed"] > 0 else "warning",
        "items_scraped": len(total_harvested_books),
        "new_items": save_stats["new"],
        "price_drops": save_stats["price_drops"],
        "price_hikes": save_stats["price_hikes"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"Harvested {len(total_harvested_books)} products & logged time-series history! Detected {save_stats['price_drops']} price drops."
    }
    return summary


if __name__ == "__main__":
    print("=========================================================")
    print("  COMPETITOR PRICE TRACKER - TIME-SERIES HISTORY ENGINE")
    print("=========================================================")
    result = run_scraper(start_page=1, max_pages=3)
    for key, value in result.items():
        print(f"  - {key}: {value}")
    print("=========================================================")
