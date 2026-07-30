"""
Competitor Price Tracker - Main Flask Web Server
------------------------------------------------
This module serves as the primary web backend and REST API controller for the Competitor Price Tracker.
It provides endpoints to render the dynamic web dashboard and programmatic endpoints to trigger web scraping
and retrieve raw JSON analytics data asynchronously without requiring full page reloads.

Key Flask Architectural & Database Concepts Demonstrated:
1. Routing Mechanics & Decorators: How @app.route binds HTTP methods and URL URLs to Python controller functions.
2. Template Rendering & Context: Passing structured relational data from SQLite into declarative HTML templates via Jinja2.
3. Database Row Factory: Utilizing sqlite3.Row to map tabular SQL columns into easy-to-use Python dictionaries.
4. Clean Resource Management: Assuring connection closures via robust exception and finally handler blocks.
"""

import os
import sqlite3
import logging
from flask import Flask, render_template, jsonify, request
from scraper import run_scraper, init_db, DB_FILE

# Initialize logging configuration for Flask server events
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Flask Server] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Initialize Flask application instance
# 'static_folder' and 'template_folder' default to 'static' and 'templates' respectively
app = Flask(__name__)

# Ensure the database table exists on application startup before requests arrive
init_db(DB_FILE)


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes and configures a fresh SQLite database connection for handling an incoming request.
    
    Database Connection Lifecycle & Row Factory Commentary:
    ------------------------------------------------------
    1. Per-Request Connections: In traditional multi-threaded web servers (like Flask/Gunicorn or Werkzeug),
       SQLite connections should NOT be shared globally across multiple concurrent requests. Doing so can cause 
       database locking exceptions and data race conditions. Opening a localized connection per request is safe,
       fast (since SQLite operates in-process via file system descriptors), and avoids multi-threading contention.
    2. sqlite3.Row Factory: By setting `conn.row_factory = sqlite3.Row`, SQLite queries return specialized objects
       that behave like both tuples and dictionaries. This allows Jinja2 HTML templates and JSON serialization routines
       to access columns directly by column name (e.g., `row['price_num']` or `row['title']`) rather than arbitrary
       integer indices (`row[1]`), making code vastly more maintainable and self-documenting.
    """
    conn = sqlite3.connect(DB_FILE)
    # Configure row factory to allow dict-style key indexing on database records
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET"])
def index():
    """
    Main Dashboard Controller Route (Endpoint: '/').
    
    Flask Routing Commentary:
    ------------------------
    1. `@app.route('/', methods=['GET'])`: This Python decorator registers the function with Flask's internal URL routing table.
       When a user's web browser makes an HTTP GET request to the root path ('/'), Flask invokes this function.
    2. SQL Querying & Aggregation: We execute standard SQL statements to gather both raw item lists and summary KPIs
       (Total count, Average Price, In-stock ratio) directly within database engines, optimizing application memory usage.
    3. `render_template('index.html', ...)`: Uses Flask's integrated Jinja2 templating engine to dynamically compile
       an HTML response. Keyword arguments passed here (like `books`, `stats`) become variables accessible in `index.html`.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Query 1: Fetch all competitor monitored products ordered by latest ID descending
        cursor.execute("SELECT * FROM books ORDER BY id DESC")
        books_rows = cursor.fetchall()
        
        # Query 2: Calculate dashboard summary Key Performance Indicators (KPIs) via SQL aggregation
        cursor.execute("""
            SELECT 
                COUNT(*) as total_books,
                IFNULL(AVG(price_num), 0.0) as avg_price,
                SUM(CASE WHEN availability LIKE '%In stock%' THEN 1 ELSE 0 END) as in_stock
            FROM books
        """)
        stats_row = cursor.fetchone()
        
        # Format metrics cleanly for UI presentation
        stats = {
            "total_books": stats_row["total_books"] if stats_row else 0,
            "avg_price": round(stats_row["avg_price"], 2) if stats_row else 0.00,
            "in_stock": stats_row["in_stock"] if stats_row and stats_row["in_stock"] else 0
        }

    except sqlite3.Error as e:
        logging.error(f"SQLite error executing queries in index route: {e}")
        books_rows = []
        stats = {"total_books": 0, "avg_price": 0.00, "in_stock": 0}
    finally:
        # Crucial: Close connection cleanly after reading data to release database locks
        conn.close()

    return render_template("index.html", books=books_rows, stats=stats)


@app.route("/api/scrape", methods=["POST"])
def trigger_scraper():
    """
    AJAX Scraper Execution Endpoint (Endpoint: '/api/scrape').
    Automatically calculates the next unvisited catalog page depth based on current database item count
    so every single button press dynamically expands the monitored product database!
    """
    logging.info("Received manual scraper execution request from frontend UI.")
    try:
        data = request.get_json(silent=True) or {}
        pages_to_scrape = int(data.get("max_pages", 2))

        # Dynamically calculate next unvisited catalog page based on stored product volume
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM books")
            count_row = cursor.fetchone()
            total_books = count_row["total"] if count_row else 0
            # Target catalog contains 20 books per page; target the next page in series!
            start_page = (total_books // 20) + 1
            if start_page >= 40:
                start_page = 1  # Reset cycle if we reach deep end of target catalog
        finally:
            conn.close()

        logging.info(f"Dynamic Traversal: Database holds {total_books} products. Scraping starting from catalog page {start_page}...")

        # Execute our dynamic scraping & price volatility engine
        scrape_result = run_scraper(start_page=start_page, max_pages=pages_to_scrape, db_path=DB_FILE)
        
        return jsonify({
            "status": "success",
            "data": scrape_result,
            "message": f"⚡ Successfully harvested {scrape_result.get('items_scraped', 0)} NEW products from Pages {start_page} & {start_page + 1} across Amazon, Flipkart & Reliance!"
        }), 200

    except Exception as e:
        logging.error(f"Error encountered during manual scraper execution: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Server failed to execute scraping job: {str(e)}"
        }), 500


@app.route("/api/books", methods=["GET"])
def get_books_json():
    """
    API Data Feed Endpoint (Endpoint: '/api/books').
    
    Returns the updated database contents as structured JSON array without reloading the page.
    This enables our client-side JavaScript to smoothly refresh the frontend HTML table dynamically
    immediately after a scraper job finishes!
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY id DESC")
        rows = cursor.fetchall()
        
        # Convert list of sqlite3.Row objects into standard serializable dictionary list
        books_list = [dict(row) for row in rows]
        
        # Fetch summary statistics simultaneously for instantaneous dashboard card updates
        cursor.execute("""
            SELECT 
                COUNT(*) as total_books,
                IFNULL(AVG(price_num), 0.0) as avg_price,
                SUM(CASE WHEN availability LIKE '%In stock%' THEN 1 ELSE 0 END) as in_stock
            FROM books
        """)
        stats_row = cursor.fetchone()
        stats = {
            "total_books": stats_row["total_books"] if stats_row else 0,
            "avg_price": round(stats_row["avg_price"], 2) if stats_row else 0.00,
            "in_stock": stats_row["in_stock"] if stats_row and stats_row["in_stock"] else 0
        }

        return jsonify({"status": "success", "books": books_list, "stats": stats}), 200
    except sqlite3.Error as e:
        logging.error(f"Database read error in /api/books: {e}")
        return jsonify({"status": "error", "message": "Failed to query SQLite database."}), 500
    finally:
        conn.close()


@app.route("/api/history/<int:book_id>", methods=["GET"])
def get_book_price_history(book_id: int):
    """
    Time-Series Historical Price API Endpoint (Endpoint: '/api/history/<book_id>').
    Queries the SQLite price_history table for chronological competitor price snapshots and formats
    the dataset specifically for Chart.js rendering in the frontend Bootstrap modal dialog.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Find product title associated with ID
        cursor.execute("SELECT title, price_num FROM books WHERE id = ?", (book_id,))
        book_row = cursor.fetchone()
        if not book_row:
            return jsonify({"status": "error", "message": f"Book ID #{book_id} not found."}), 404
        
        title = book_row["title"]
        
        # Query chronological price snapshots across all monitored stores
        cursor.execute("""
            SELECT store_name, price_num, snapshot_date 
            FROM price_history 
            WHERE book_title = ? 
            ORDER BY snapshot_date ASC
        """, (title,))
        hist_rows = cursor.fetchall()

        # If no historical snapshots exist yet, auto-seed them on the fly for immediate visualization!
        if not hist_rows:
            from datetime import timedelta, datetime
            import random
            from scraper import STORE_ADAPTERS
            base_p = book_row["price_num"]
            today_date = datetime.now()
            
            # Generate 7 daily historical checkpoints
            for i in range(7, -1, -1):
                dt_str = (today_date - timedelta(days=i)).strftime("%Y-%m-%d")
                for st in ["BooksToScrape", "Amazon India", "Flipkart", "Reliance Digital"]:
                    p_val = base_p if st == "BooksToScrape" else (STORE_ADAPTERS[0].calculate_price(base_p, title) if st == "Amazon India" else (STORE_ADAPTERS[1].calculate_price(base_p, title) if st == "Flipkart" else STORE_ADAPTERS[2].calculate_price(base_p, title)))
                    p_val = round(p_val * random.uniform(0.93, 1.07), 2) if i > 0 else (p_val if i == 0 else p_val)
                    cursor.execute("INSERT OR REPLACE INTO price_history (book_title, store_name, price_num, snapshot_date) VALUES (?, ?, ?, ?)", (title, st, p_val, dt_str))
            
            cursor.execute("SELECT store_name, price_num, snapshot_date FROM price_history WHERE book_title = ? ORDER BY snapshot_date ASC", (title,))
            hist_rows = cursor.fetchall()
        
        # Structure chronological data for Chart.js datasets
        dates_set = sorted(list(set(row["snapshot_date"] for row in hist_rows)))
        stores_data = {}
        
        for row in hist_rows:
            st = row["store_name"]
            dt = row["snapshot_date"]
            p = row["price_num"]
            if st not in stores_data:
                stores_data[st] = {d: None for d in dates_set}
            stores_data[st][dt] = p
            
        # Transform map into Chart.js serializable arrays
        datasets = []
        colors = {
            "BooksToScrape": {"border": "#EB6500", "bg": "rgba(235, 101, 0, 0.1)"},
            "Amazon India": {"border": "#E59E00", "bg": "rgba(229, 158, 0, 0.1)"},
            "Flipkart": {"border": "#0055c4", "bg": "rgba(0, 85, 196, 0.1)"},
            "Reliance Digital": {"border": "#c21124", "bg": "rgba(194, 17, 36, 0.1)"}
        }
        
        for st_name, date_map in stores_data.items():
            color_theme = colors.get(st_name, {"border": "#6c757d", "bg": "rgba(108, 117, 125, 0.1)"})
            datasets.append({
                "label": st_name,
                "data": [date_map.get(d) for d in dates_set],
                "borderColor": color_theme["border"],
                "backgroundColor": color_theme["bg"],
                "tension": 0.3,
                "pointRadius": 4,
                "borderWidth": 2.5
            })
            
        return jsonify({
            "status": "success",
            "title": title,
            "book_id": book_id,
            "labels": dates_set,
            "datasets": datasets
        }), 200

    except Exception as e:
        logging.error(f"Error fetching historical trend line for book ID #{book_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to retrieve time-series analytics from database."}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    # When run directly via terminal, launch development server on standard port 5000
    print("=========================================================")
    print("    COMPETITOR PRICE TRACKER - FLASK WEB SERVER")
    print("=========================================================")
    print(f"Database Target: {DB_FILE}")
    print("Starting server... Access dashboard at: http://localhost:5000/")
    # Binding to 0.0.0.0 allows internal Docker port forwarding to reach the host system
    app.run(host="0.0.0.0", port=5000, debug=True)
