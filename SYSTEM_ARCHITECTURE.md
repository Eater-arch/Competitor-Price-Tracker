# 🏢 Enterprise Competitor Price Tracker - System Architecture

```mermaid
graph TD
    %% =======================================================
    %% LAYER 1: FRONTEND WEB UI
    %% =======================================================
    subgraph UI ["Frontend Web UI (Bootstrap 5 SPA)"]
        Dashboard["index.html / Main Dashboard View"]
    end

    %% Connect UI to JS Logic Models
    Dashboard <-->|DOM Binding & Events| ScraperController["ScraperExecutionController"]
    Dashboard <-->|DOM Binding & Events| TableModel["TableDataViewModel"]
    Dashboard <-->|DOM Binding & Events| FilterModel["SearchFilterViewModel"]
    Dashboard <-->|DOM Binding & Events| ChartModel["ChartModalViewModel"]

    %% =======================================================
    %% LAYER 2: CLIENT-SIDE CONTROLLERS (VANILLA JS / CHART.JS)
    %% =======================================================
    subgraph Client ["Client-Side Controllers & ViewModel (script.js)"]
        ScraperController
        TableModel
        FilterModel
        ChartModel
    end

    %% Connect JS Models to Flask Backend via REST APIs
    ScraperController -->|POST /api/scrape| FlaskAPI["Flask Router & API Gateway"]
    TableModel -->|GET /api/books| FlaskAPI
    FilterModel -.->|In-Memory DOM Filtering| TableModel
    ChartModel -->|GET /api/history/id| FlaskAPI

    %% =======================================================
    %% LAYER 3: PYTHON CORE BACKEND & RELATIONAL DATA STORAGE
    %% =======================================================
    subgraph Backend ["Python Core Backend & Relational Data Storage (Flask / SQLite3)"]
        FlaskAPI
        
        ScraperEngine["Scraping Engine (Requests & BeautifulSoup4)"]
        AdapterEngine["OOP Store Adapters (Amazon, Flipkart, Reliance)"]
        
        DBManager["Database Manager (SQLite Relational Schema)"]
        HistoryManager["Time-Series Storage (price_history Table)"]
    end

    %% Internal Backend & Database Flow
    FlaskAPI -->|Trigger Manual Harvest| ScraperEngine
    FlaskAPI <-->|Query Monitored Products| DBManager
    FlaskAPI <-->|Query Chronological Analytics| HistoryManager

    ScraperEngine -->|Raw Catalog SKUs & Prices| AdapterEngine
    AdapterEngine -->|Multi-Store Offer Array| DBManager
    AdapterEngine -->|Daily Time-Series Snapshot| HistoryManager
    DBManager -.->|Foreign Key & Title Mapping| HistoryManager

    %% =======================================================
    %% STYLE CUSTOMIZATIONS (Dark / Minimalist Sample Theme)
    %% =======================================================
    style UI fill:#2b2d30,stroke:#6c757d,stroke-width:2px,color:#fff
    style Client fill:#2b2d30,stroke:#6c757d,stroke-width:2px,color:#fff
    style Backend fill:#2b2d30,stroke:#6c757d,stroke-width:2px,color:#fff
    style Dashboard fill:#1e1f22,stroke:#4a4d52,stroke-width:2px,color:#fff
    style ScraperController fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style TableModel fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style FilterModel fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style ChartModel fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style FlaskAPI fill:#1e1f22,stroke:#4a4d52,stroke-width:2px,color:#ffc107
    style ScraperEngine fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style AdapterEngine fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style DBManager fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
    style HistoryManager fill:#1e1f22,stroke:#4a4d52,stroke-width:1.5px,color:#fff
```

---

## 📋 Architectural Overview (For PowerPoint Slide Text)
* **Tier 1 (Frontend UI)**: Represents our Single-Page Application (SPA) view rendered via `index.html`. It communicates with underlying controllers through standard event delegation and responsive DOM property bindings.
* **Tier 2 (Client-Side Logic / ViewModels)**: Organizes our frontend functionality into modular controllers (`ScraperExecutionController`, `TableDataViewModel`, `SearchFilterViewModel`, and `ChartModalViewModel`). These manage user inputs and communicate asynchronously with the backend server without requiring page reloads.
* **Tier 3 (Python Core Backend & Storage)**: The engine room of the software. An HTTP request intercepted by the `Flask Router & API Gateway` is routed to the `Scraping Engine` for network harvesting or straight to the `Database Manager` and `Time-Series Storage` layers to serve low-latency analytics payloads back to the dashboard!
