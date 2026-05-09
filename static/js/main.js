// ========================================
// Trading Platform - Dark Theme JavaScript
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeDarkTheme();
    setupAnimations();
    setupInteractivity();
    setupChartDefaults();
});

// ========================================
// DARK THEME INITIALIZATION
// ========================================

function initializeDarkTheme() {
    // Check for saved theme preference or default to dark
    const savedTheme = localStorage.getItem('trading-theme') || 'dark';
    setTheme(savedTheme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('trading-theme', theme);
}

// ========================================
// ANIMATIONS
// ========================================

function setupAnimations() {
    // Animate cards on scroll
    observeElements('.card', 'animate-slide');
    observeElements('.trading-card', 'animate-slide');
    
    // Animate gain/loss percentages
    animatePercentages();
    
    // Glow effect on hover
    addGlowEffect();
}

function observeElements(selector, animationClass) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add(animationClass);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll(selector).forEach(el => observer.observe(el));
}

function animatePercentages() {
    const percentages = document.querySelectorAll('.percentage-change');
    percentages.forEach(el => {
        const value = parseFloat(el.textContent);
        el.classList.add(value >= 0 ? 'positive' : 'negative');
        
        // Animate the number count-up
        const finalValue = el.textContent;
        let currentValue = 0;
        const increment = value / 20;
        const interval = setInterval(() => {
            currentValue += increment;
            if ((increment > 0 && currentValue >= value) || (increment < 0 && currentValue <= value)) {
                el.textContent = finalValue;
                clearInterval(interval);
            } else {
                el.textContent = currentValue.toFixed(2) + '%';
            }
        }, 30);
    });
}

function addGlowEffect() {
    const cards = document.querySelectorAll('.card, .trading-card, .btn-primary');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = 'var(--shadow-glow), 0 8px 32px rgba(0, 212, 255, 0.2)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '';
        });
    });
}

// ========================================
// INTERACTIVE ELEMENTS
// ========================================

function setupInteractivity() {
    setupTableRowHover();
    setupFormValidation();
    setupModals();
    setupTooltips();
}

function setupTableRowHover() {
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'var(--hover-bg)';
            });
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    });
}

function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                addShakeAnimation(this);
            }
            this.classList.add('was-validated');
        });
    });
}

function setupModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function() {
            this.style.animation = 'fadeIn 0.3s ease-out';
        });
    });
}

function setupTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function addShakeAnimation(element) {
    element.style.animation = 'shake 0.4s ease-in-out';
    setTimeout(() => {
        element.style.animation = '';
    }, 400);
}

// ========================================
// CHART.JS CONFIGURATION
// ========================================

function setupChartDefaults() {
    const darkThemeColors = {
        textColor: '#e8eef5',
        gridColor: '#2d3546',
        accentPrimary: '#00d4ff',
        accentSecondary: '#2ed573',
        accentDanger: '#ff4757',
        accentWarning: '#ffa502'
    };
    
    // Set Chart.js defaults
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = darkThemeColors.textColor;
        Chart.defaults.borderColor = darkThemeColors.gridColor;
        
        // Configure axes
        Chart.defaults.scale.grid.color = darkThemeColors.gridColor;
        Chart.defaults.scale.ticks.color = darkThemeColors.textColor;
        Chart.defaults.scale.title.color = darkThemeColors.textColor;
        
        // Configure tooltips
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 20, 25, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = darkThemeColors.accentPrimary;
        Chart.defaults.plugins.tooltip.bodyColor = darkThemeColors.textColor;
        Chart.defaults.plugins.tooltip.borderColor = darkThemeColors.accentPrimary;
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.displayColors = true;
    }
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function getTradeColor(value) {
    return value >= 0 ? '#2ed573' : '#ff4757';
}

// ========================================
// REAL-TIME DATA UPDATES (if websockets enabled)
// ========================================

function setupRealtimeUpdates() {
    // This is a placeholder for WebSocket integration
    // Implement based on your Django Channels setup
    
    const elements = document.querySelectorAll('[data-live-update]');
    if (elements.length > 0) {
        console.log('Live update elements detected. Connect WebSocket here.');
    }
}

// ========================================
// PRICE TICKER ANIMATION
// ========================================

function animatePriceTickers() {
    const tickers = document.querySelectorAll('[data-price]');
    tickers.forEach(ticker => {
        const oldPrice = parseFloat(ticker.textContent);
        const newPrice = parseFloat(ticker.getAttribute('data-price'));
        
        if (oldPrice !== newPrice) {
            // Flash animation
            ticker.style.backgroundColor = newPrice > oldPrice ? 
                'rgba(46, 213, 115, 0.2)' : 
                'rgba(255, 71, 87, 0.2)';
            
            setTimeout(() => {
                ticker.style.backgroundColor = '';
                ticker.textContent = formatCurrency(newPrice);
            }, 500);
        }
    });
}

// ========================================
// PERFORMANCE METRICS TRACKING
// ========================================

function trackPortfolioPerformance() {
    const performanceCards = document.querySelectorAll('[data-metric]');
    performanceCards.forEach(card => {
        const metric = card.getAttribute('data-metric');
        const value = parseFloat(card.getAttribute('data-value'));
        
        // Add visual indicator
        if (value > 0) {
            card.classList.add('gain');
        } else if (value < 0) {
            card.classList.add('loss');
        }
    });
}

// ========================================
// EXPORT AND DOWNLOAD FUNCTIONS
// ========================================

function exportToCSV(tableElement, filename) {
    let csv = [];
    const rows = tableElement.querySelectorAll('tr');
    
    rows.forEach(row => {
        let csvRow = [];
        const cols = row.querySelectorAll('td, th');
        cols.forEach(col => {
            csvRow.push('"' + col.textContent + '"');
        });
        csv.push(csvRow.join(','));
    });
    
    downloadCSV(csv.join('\n'), filename);
}

function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(csvFile);
    downloadLink.download = filename;
    downloadLink.click();
}

// ========================================
// KEYBOARD SHORTCUTS
// ========================================

document.addEventListener('keydown', function(event) {
    // Ctrl+D or Cmd+D for Dashboard
    if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
        event.preventDefault();
        window.location.href = '/dashboard/';
    }
    
    // Ctrl+P or Cmd+P for Portfolio
    if ((event.ctrlKey || event.metaKey) && event.key === 'p') {
        event.preventDefault();
        window.location.href = '/portfolio/';
    }
});

// ========================================
// INITIALIZATION
// ========================================

// Run additional setups
setupRealtimeUpdates();
animatePriceTickers();
trackPortfolioPerformance();
