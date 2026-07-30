/*
 * Competitor Price Tracker - Frontend Interactive Logic & Chart.js Integration
 * Handles AJAX scraper execution, interactive Chart.js time-series historical modal rendering via event delegation,
 * multi-store pricing offers, Best Deal badges, and instant title filtering.
 */

let activePriceChart = null;

/**
 * Global handler invoked when user clicks any book title link in the dashboard table.
 * Opens the interactive time-series modal and dynamically renders Chart.js trajectories!
 */
window.openPriceChart = async function(bookId, bookTitle) {
    const modalElement = document.getElementById('chartModal');
    const titleEl = document.getElementById('chartModalTitle');
    const spinnerEl = document.getElementById('chartLoadingSpinner');
    const chartContainerEl = document.getElementById('chartContainer');
    const errorEl = document.getElementById('chartErrorMessage');

    if (!modalElement) {
        console.error('Modal element #chartModal not found in DOM.');
        return;
    }

    // Securely open Bootstrap 5 Modal
    let modalInstance = bootstrap.Modal.getInstance(modalElement);
    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalElement);
    }
    modalInstance.show();

    if (titleEl) titleEl.textContent = `Historical Trend: "${bookTitle}"`;
    if (spinnerEl) spinnerEl.style.display = 'block';
    if (chartContainerEl) chartContainerEl.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';

    try {
        const response = await fetch(`/api/history/${bookId}`);
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            if (spinnerEl) spinnerEl.style.display = 'none';
            if (chartContainerEl) chartContainerEl.style.display = 'block';

            const canvas = document.getElementById('priceTrendChart');
            if (canvas) {
                if (activePriceChart) {
                    activePriceChart.destroy();
                }

                const ctx = canvas.getContext('2d');
                activePriceChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: result.labels,
                        datasets: result.datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    font: { family: "'Outfit', sans-serif", weight: '600', size: 13 },
                                    padding: 18,
                                    usePointStyle: true
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(33, 37, 41, 0.95)',
                                titleFont: { family: "'Outfit', sans-serif", size: 14, weight: '700' },
                                bodyFont: { family: "'JetBrains Mono', monospace", size: 13 },
                                padding: 12,
                                cornerRadius: 8,
                                callbacks: {
                                    label: function(context) {
                                        let label = context.dataset.label || '';
                                        if (label) label += ': ';
                                        if (context.parsed.y !== null) {
                                            label += '₹' + context.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                                        }
                                        return label;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: { color: 'rgba(0,0,0,0.04)' },
                                title: { display: true, text: 'Chronological Snapshot Date', font: { weight: '700', size: 12 } }
                            },
                            y: {
                                grid: { color: 'rgba(0,0,0,0.06)' },
                                title: { display: true, text: 'Converted Retail Price (INR ₹)', font: { weight: '700', size: 12 } },
                                ticks: {
                                    callback: function(value) {
                                        return '₹' + value.toLocaleString('en-IN');
                                    }
                                }
                            }
                        }
                    }
                });
            }
        } else {
            throw new Error(result.message || 'Server returned invalid history payload.');
        }
    } catch (error) {
        console.error('Error fetching historical time-series analytics:', error);
        if (spinnerEl) spinnerEl.style.display = 'none';
        if (errorEl) {
            errorEl.textContent = `❌ Could not load historical time-series chart: ${error.message}`;
            errorEl.style.display = 'block';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const runScraperBtn = document.getElementById('runScraperBtn');
    const searchFilterInput = document.getElementById('searchFilter');
    const tableBody = document.getElementById('booksTableBody');
    const alertContainer = document.getElementById('alertContainer');

    const totalBooksCountEl = document.getElementById('totalBooksCount');
    const avgPriceEl = document.getElementById('avgPriceCount');
    const inStockCountEl = document.getElementById('inStockCount');
    const lastScrapingTimestampEl = document.getElementById('lastScrapeTime');

    // Global Event Delegation: Captures clicks on any interactive book title link (static or dynamic)
    document.addEventListener('click', (e) => {
        const link = e.target.closest('.book-title-link');
        if (link) {
            e.preventDefault();
            const bookId = link.getAttribute('data-book-id');
            const bookTitle = link.getAttribute('data-book-title');
            if (bookId && bookTitle) {
                window.openPriceChart(bookId, bookTitle);
            }
        }
    });

    async function executeManualScrape() {
        if (!runScraperBtn) return;

        const originalText = runScraperBtn.innerHTML;
        runScraperBtn.disabled = true;
        runScraperBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm text-white" role="status" aria-hidden="true"></span>
            <span>Harvesting New Items & History...</span>
        `;
        
        showNotification(`⚡ Scraper active: Scanning remote catalog for NEW products & generating time-series checkpoints...`, 'info');

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ max_pages: 2 })
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                showNotification(result.message || `⚡ Scraper run successful! Database catalog updated.`, 'success');
                
                if (lastScrapingTimestampEl) {
                    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    lastScrapingTimestampEl.textContent = `Last run at ${timeNow}`;
                }

                await fetchAndUpdateTableData(true);
            } else {
                showNotification(`⚠️ Scraper returned a warning: ${result.message || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('AJAX Error triggering scraper:', error);
            showNotification('❌ Network error: Could not reach backend server to execute scraper.', 'error');
        } finally {
            runScraperBtn.disabled = false;
            runScraperBtn.innerHTML = originalText;
        }
    }

    async function fetchAndUpdateTableData(isAfterScrape = false) {
        try {
            const response = await fetch('/api/books', { method: 'GET' });
            const data = await response.json();

            if (response.ok && data.status === 'success') {
                updateKpiCard(totalBooksCountEl, data.stats.total_books, '', 0);
                updateKpiCard(avgPriceEl, data.stats.avg_price, '₹', 2);
                updateKpiCard(inStockCountEl, data.stats.in_stock, '', 0);

                renderBooksTable(data.books, isAfterScrape);
            }
        } catch (error) {
            console.error('Failed to fetch updated books table data:', error);
        }
    }

    function formatCurrency(number) {
        const val = parseFloat(number) || 0.0;
        return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function renderBooksTable(booksArray, isAfterScrape = false) {
        if (!tableBody) return;
        tableBody.innerHTML = '';

        if (!booksArray || booksArray.length === 0) {
            tableBody.innerHTML = `
                <tr id="emptyStateRow">
                    <td colspan="5" class="text-center py-5 text-muted">
                        <i class="bi bi-inbox fs-1 d-block mb-3"></i>
                        <h5>No products monitored in SQLite database yet.</h5>
                        <p class="small">Click <strong>'Run Scraper'</strong> above to begin harvesting competitor pricing!</p>
                    </td>
                </tr>
            `;
            return;
        }

        booksArray.forEach((book, index) => {
            const tr = document.createElement('tr');
            if (isAfterScrape && (book.price_direction !== 'same' || index < 20)) {
                tr.className = 'row-recently-updated';
            }
            
            const isAvailable = book.availability && book.availability.toLowerCase().includes('in stock');
            const availabilityHtml = isAvailable 
                ? `<span class="badge-status badge-in-stock"><i class="bi bi-check-circle-fill"></i> In Stock</span>`
                : `<span class="badge-status badge-out-stock"><i class="bi bi-exclamation-triangle-fill"></i> Out of Stock</span>`;

            const ratingHtml = `<span class="badge-rating"><i class="bi bi-star-fill text-warning"></i> ${book.rating || 'N/A'}</span>`;

            let deltaHtml = '';
            if (book.price_direction === 'drop' && book.price_delta_str) {
                deltaHtml = `<span class="price-delta-badge delta-drop">${escapeHtml(book.price_delta_str)}</span>`;
            } else if (book.price_direction === 'hike' && book.price_delta_str) {
                deltaHtml = `<span class="price-delta-badge delta-hike">${escapeHtml(book.price_delta_str)}</span>`;
            } else if (book.price_direction === 'new' && book.price_delta_str) {
                deltaHtml = `<span class="price-delta-badge delta-new">${escapeHtml(book.price_delta_str)}</span>`;
            }

            const amzPrice = formatCurrency(book.price_amazon);
            const flpPrice = formatCurrency(book.price_flipkart);
            const relPrice = formatCurrency(book.price_reliance);
            const bestPrice = formatCurrency(book.best_price || book.price_num);
            const bestStore = book.best_store || 'BooksToScrape';

            tr.innerHTML = `
                <td>
                    <a href="javascript:void(0);" class="book-title-link d-flex align-items-center text-decoration-none" data-book-id="${book.id}" data-book-title="${escapeHtml(book.title)}" title="Click to view interactive Historical Price Trend Chart!">
                        <i class="bi bi-graph-up-arrow fs-5 me-2 text-saffron-chart-icon"></i>
                        <span class="book-title fw-bold text-dark">${escapeHtml(book.title)}</span>
                    </a>
                    <div class="text-muted small ms-4">ID: #${book.id} • ${escapeHtml(book.last_updated)}</div>
                </td>
                <td>
                    <span class="book-price">${escapeHtml(book.price_str)}</span>
                    ${deltaHtml}
                </td>
                <td>
                    <div class="store-clash-grid">
                        <div class="store-offer">
                            <span class="store-name"><i class="bi bi-cart2 text-warning"></i> Amazon IN:</span>
                            <span class="store-price">₹${amzPrice}</span>
                        </div>
                        <div class="store-offer">
                            <span class="store-name"><i class="bi bi-bag-check text-primary"></i> Flipkart:</span>
                            <span class="store-price">₹${flpPrice}</span>
                        </div>
                        <div class="store-offer">
                            <span class="store-name"><i class="bi bi-shop text-danger"></i> Reliance:</span>
                            <span class="store-price">₹${relPrice}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge-best-deal">
                        <i class="bi bi-fire fs-6 text-danger"></i>
                        <span>Best Deal: <strong>${escapeHtml(bestStore)}</strong> (₹${bestPrice})</span>
                    </span>
                </td>
                <td>
                    <div class="d-flex flex-column gap-1 align-items-start">
                        ${availabilityHtml}
                        ${ratingHtml}
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });

        if (searchFilterInput && searchFilterInput.value.trim() !== '') {
            filterTableRows(searchFilterInput.value.trim().toLowerCase());
        }
    }

    function filterTableRows(searchQuery) {
        if (!tableBody) return;
        const rows = tableBody.querySelectorAll('tr:not(#emptyStateRow)');
        let visibleCount = 0;

        rows.forEach(row => {
            const titleCell = row.querySelector('.book-title');
            if (titleCell) {
                const rowText = row.textContent.toLowerCase();
                if (rowText.includes(searchQuery)) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            }
        });

        let filterEmptyRow = document.getElementById('filterEmptyRow');
        if (visibleCount === 0 && rows.length > 0) {
            if (!filterEmptyRow) {
                filterEmptyRow = document.createElement('tr');
                filterEmptyRow.id = 'filterEmptyRow';
                filterEmptyRow.innerHTML = `
                    <td colspan="5" class="text-center py-4 text-muted">
                        No book products found matching filter: "<strong>${escapeHtml(searchQuery)}</strong>"
                    </td>
                `;
                tableBody.appendChild(filterEmptyRow);
            }
        } else if (filterEmptyRow) {
            filterEmptyRow.remove();
        }
    }

    function showNotification(message, type = 'info') {
        if (!alertContainer) return;
        const alertEl = document.createElement('div');
        alertEl.className = `custom-alert ${type === 'error' ? 'error' : ''}`;
        
        const icon = type === 'success' ? 'bi-check-circle-fill text-success' :
                     type === 'error' ? 'bi-exclamation-triangle-fill text-danger' : 'bi-info-circle-fill text-info';
                     
        alertEl.innerHTML = `
            <i class="bi ${icon} fs-4"></i>
            <div class="flex-grow-1">
                <div class="fw-medium">${message}</div>
            </div>
            <button type="button" class="btn-close" aria-label="Close"></button>
        `;

        const closeBtn = alertEl.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => alertEl.remove());
        alertContainer.appendChild(alertEl);

        setTimeout(() => {
            if (alertEl.parentNode) {
                alertEl.style.opacity = '0';
                alertEl.style.transition = 'opacity 0.5s ease';
                setTimeout(() => alertEl.remove(), 500);
            }
        }, 5500);
    }

    function updateKpiCard(element, targetValue, prefix = '', decimals = 0) {
        if (!element) return;
        const startValue = parseFloat(element.getAttribute('data-val') || 0);
        const endValue = parseFloat(targetValue);
        const duration = 800;
        const startTime = performance.now();

        function animate(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const easeProgress = 1 - (1 - progress) * (1 - progress);
            const currentValue = startValue + (endValue - startValue) * easeProgress;
            element.textContent = `${prefix}${currentValue.toFixed(decimals)}`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.setAttribute('data-val', endValue);
            }
        }
        requestAnimationFrame(animate);
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe.toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    if (runScraperBtn) {
        runScraperBtn.addEventListener('click', executeManualScrape);
    }
    if (searchFilterInput) {
        searchFilterInput.addEventListener('input', (e) => {
            filterTableRows(e.target.value.trim().toLowerCase());
        });
    }

    if (totalBooksCountEl) totalBooksCountEl.setAttribute('data-val', totalBooksCountEl.textContent || '0');
    if (avgPriceEl) avgPriceEl.setAttribute('data-val', avgPriceEl.textContent.replace('₹', '') || '0');
    if (inStockCountEl) inStockCountEl.setAttribute('data-val', inStockCountEl.textContent || '0');
});
