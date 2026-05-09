// ========================================
// Trading Platform - Dark Theme JavaScript
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeDarkTheme();
    setupAnimations();
    setupInteractivity();
    setupChartDefaults();
    initializeMarketCharts(document);
});

document.body.addEventListener('htmx:afterSwap', function(event) {
    initializeMarketCharts(event.target);
    setupTooltips();
});

document.body.addEventListener('htmx:beforeSwap', function(event) {
    disposeMarketCharts(event.detail.target);
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
        if (Chart.defaults.scale) {
            Chart.defaults.scale.grid.color = darkThemeColors.gridColor;
            Chart.defaults.scale.ticks.color = darkThemeColors.textColor;
            Chart.defaults.scale.title.color = darkThemeColors.textColor;
        }
        
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
// MARKET CHARTS
// ========================================

const marketChartRegistry = new Map();
let marketChartPluginsRegistered = false;

function initializeMarketCharts(root) {
    if (typeof Chart === 'undefined') {
        return;
    }

    registerMarketChartPlugins();
    findMarketChartCards(root).forEach(card => setupMarketChartCard(card));
}

function findMarketChartCards(root) {
    const cards = [];
    if (!root) {
        return cards;
    }
    if (root.nodeType === 1 && root.matches('[data-market-chart]')) {
        cards.push(root);
    }
    if (root.querySelectorAll) {
        root.querySelectorAll('[data-market-chart]').forEach(card => cards.push(card));
    }
    return cards;
}

function setupMarketChartCard(card) {
    if (card.dataset.chartInitialized === 'true') {
        return;
    }

    card.dataset.chartInitialized = 'true';
    const payload = readMarketChartPayload(card);
    const intervalSelect = card.querySelector('[data-chart-interval]');
    const persistedAuto = card.dataset.persistAutoRefresh;
    const persistedInterval = card.dataset.persistInterval;
    const state = {
        card: card,
        payload: payload,
        chart: null,
        view: 'line',
        indicators: {
            ema: true,
            sma: false,
            rsi: false,
            macd: false,
            bollinger: false
        },
        visibleStart: 0,
        visibleEnd: payload ? Math.max(payload.rows.length - 1, 0) : 0,
        refreshInterval: Number(persistedInterval || (intervalSelect && intervalSelect.value) || card.dataset.refreshInterval || 45),
        autoRefresh: persistedAuto === undefined ? true : persistedAuto === '1',
        refreshTimer: null,
        countdownTimer: null,
        nextRefreshAt: null,
        dragState: null
    };

    card._marketChartState = state;
    marketChartRegistry.set(card.id, state);
    applyPersistedRefreshControls(state);
    bindMarketChartControls(state);

    if (payload && payload.rows.length) {
        renderMarketChart(state);
        updateMarketChartStatus(state);
    }

    scheduleMarketChartRefresh(state);
}

function disposeMarketCharts(root) {
    findMarketChartCards(root).forEach(disposeMarketChart);
}

function disposeMarketChart(card) {
    const state = card && (card._marketChartState || marketChartRegistry.get(card.id));
    if (!state) {
        return;
    }
    clearTimeout(state.refreshTimer);
    clearInterval(state.countdownTimer);
    if (state.chart) {
        state.chart.destroy();
    }
    marketChartRegistry.delete(card.id);
}

function readMarketChartPayload(card) {
    const jsonId = card.dataset.jsonId;
    const script = jsonId ? document.getElementById(jsonId) : null;
    if (!script || !script.textContent.trim()) {
        return null;
    }
    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Could not parse market chart data.', error);
        return null;
    }
}

function registerMarketChartPlugins() {
    if (marketChartPluginsRegistered || typeof Chart === 'undefined') {
        return;
    }

    Chart.register({
        id: 'marketCrosshair',
        afterDraw(chart) {
            const active = chart.tooltip && chart.tooltip._active;
            if (!active || !active.length) {
                return;
            }

            const {ctx, chartArea} = chart;
            const point = active[0].element;
            ctx.save();
            ctx.strokeStyle = 'rgba(232, 238, 245, 0.34)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(point.x, chartArea.top);
            ctx.lineTo(point.x, chartArea.bottom);
            ctx.moveTo(chartArea.left, point.y);
            ctx.lineTo(chartArea.right, point.y);
            ctx.stroke();
            ctx.restore();
        }
    });

    Chart.register({
        id: 'marketCandlesticks',
        afterDatasetsDraw(chart) {
            const marketState = chart.$marketChart;
            if (!marketState || marketState.view !== 'candlestick') {
                return;
            }

            const rows = marketState.payload.rows;
            const xScale = chart.scales.x;
            const yScale = chart.scales.y;
            const {ctx, chartArea} = chart;
            const start = Math.max(0, Math.floor(marketState.visibleStart));
            const end = Math.min(rows.length - 1, Math.ceil(marketState.visibleEnd));
            const visibleCount = Math.max(end - start + 1, 1);
            const candleWidth = Math.max(3, Math.min(14, chartArea.width / visibleCount * 0.58));

            ctx.save();
            for (let index = start; index <= end; index += 1) {
                const row = rows[index];
                if (!row) {
                    continue;
                }

                const x = xScale.getPixelForValue(index);
                const openY = yScale.getPixelForValue(row.open);
                const closeY = yScale.getPixelForValue(row.close);
                const highY = yScale.getPixelForValue(row.high);
                const lowY = yScale.getPixelForValue(row.low);
                const isUp = row.close >= row.open;
                const color = isUp ? '#2ed573' : '#ff4757';
                const bodyTop = Math.min(openY, closeY);
                const bodyHeight = Math.max(Math.abs(openY - closeY), 1.5);

                ctx.strokeStyle = color;
                ctx.fillStyle = isUp ? 'rgba(46, 213, 115, 0.22)' : 'rgba(255, 71, 87, 0.28)';
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(x, highY);
                ctx.lineTo(x, lowY);
                ctx.stroke();
                ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
                ctx.strokeRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
            }
            ctx.restore();
        }
    });

    marketChartPluginsRegistered = true;
}

function bindMarketChartControls(state) {
    const card = state.card;

    card.querySelectorAll('[data-chart-view]').forEach(button => {
        button.addEventListener('click', () => {
            state.view = button.dataset.chartView;
            setGroupedButtonActive(card.querySelectorAll('[data-chart-view]'), button);
            applyMarketChartVisibility(state);
        });
    });

    card.querySelectorAll('[data-chart-toggle]').forEach(button => {
        button.addEventListener('click', () => {
            const key = button.dataset.chartToggle;
            state.indicators[key] = !state.indicators[key];
            setToggleButtonState(button, state.indicators[key]);
            applyMarketChartVisibility(state);
        });
    });

    card.querySelectorAll('[data-chart-timeframe]').forEach(button => {
        button.addEventListener('click', () => {
            setGroupedButtonActive(card.querySelectorAll('[data-chart-timeframe]'), button);
            refreshMarketChart(state, {timeframe: button.dataset.chartTimeframe, live: false});
        });
    });

    card.querySelectorAll('[data-chart-refresh]').forEach(button => {
        button.addEventListener('click', () => refreshMarketChart(state, {live: true}));
    });

    const autoRefresh = card.querySelector('[data-chart-autorefresh]');
    if (autoRefresh) {
        autoRefresh.addEventListener('change', () => {
            state.autoRefresh = autoRefresh.checked;
            scheduleMarketChartRefresh(state);
        });
    }

    const intervalSelect = card.querySelector('[data-chart-interval]');
    if (intervalSelect) {
        intervalSelect.addEventListener('change', () => {
            state.refreshInterval = Number(intervalSelect.value);
            scheduleMarketChartRefresh(state);
        });
    }

    card.querySelectorAll('[data-chart-action]').forEach(button => {
        button.addEventListener('click', () => {
            const action = button.dataset.chartAction;
            if (action === 'zoom-in') {
                zoomMarketChart(state, 0.72);
            } else if (action === 'zoom-out') {
                zoomMarketChart(state, 1.35);
            } else if (action === 'reset-zoom') {
                resetMarketChartZoom(state);
            }
        });
    });
}

function applyPersistedRefreshControls(state) {
    const autoRefresh = state.card.querySelector('[data-chart-autorefresh]');
    const intervalSelect = state.card.querySelector('[data-chart-interval]');
    if (autoRefresh) {
        autoRefresh.checked = state.autoRefresh;
    }
    if (intervalSelect) {
        intervalSelect.value = String(state.refreshInterval);
    }
}

function renderMarketChart(state) {
    const canvas = state.card.querySelector('canvas.market-chart-canvas');
    if (!canvas || !state.payload) {
        return;
    }

    const rows = state.payload.rows;
    const labels = rows.map(row => row.timestampLabel);
    const maxVolume = Math.max(...rows.map(row => Number(row.volume) || 0), 1);
    const currency = state.payload.currency || 'USD';

    state.chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: buildMarketChartDatasets(rows)
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            normalized: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                decimation: {
                    enabled: true,
                    algorithm: 'lttb',
                    samples: 420
                },
                tooltip: {
                    filter: tooltipItem => !tooltipItem.dataset.tooltipHidden,
                    callbacks: {
                        title(items) {
                            const row = rowFromTooltip(items[0], rows);
                            return row ? row.timestampLabel : '';
                        },
                        beforeBody(items) {
                            const row = rowFromTooltip(items[0], rows);
                            if (!row || state.view !== 'candlestick') {
                                return [];
                            }
                            return [
                                `Open: ${formatCurrency(row.open, currency)}`,
                                `High: ${formatCurrency(row.high, currency)}`,
                                `Low: ${formatCurrency(row.low, currency)}`,
                                `Close: ${formatCurrency(row.close, currency)}`
                            ];
                        },
                        label(context) {
                            return marketTooltipLabel(context, currency);
                        },
                        afterBody(items) {
                            const row = rowFromTooltip(items[0], rows);
                            if (!row) {
                                return [];
                            }
                            return [
                                `Change: ${formatPercentPoints(row.changePercent)}`,
                                `Volume: ${formatVolume(row.volume)}`,
                                `Momentum: ${formatSignedNumber(row.momentum)}`,
                                `Velocity: ${formatPercentPoints(row.velocity)}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'category',
                    min: state.visibleStart,
                    max: state.visibleEnd,
                    grid: {
                        color: 'rgba(45, 53, 70, 0.6)'
                    },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 8,
                        maxRotation: 0,
                        callback(value, index) {
                            const row = rows[value] || rows[index];
                            if (!row) {
                                return '';
                            }
                            return compactTimestamp(row.timestamp);
                        }
                    }
                },
                y: {
                    position: 'left',
                    min: state.payload.priceAxis.min,
                    max: state.payload.priceAxis.max,
                    ticks: {
                        stepSize: state.payload.priceAxis.step,
                        callback(value) {
                            return formatAxisCurrency(value, currency);
                        }
                    },
                    grid: {
                        color: 'rgba(45, 53, 70, 0.72)'
                    }
                },
                rsi: {
                    position: 'right',
                    display: false,
                    min: 0,
                    max: 100,
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        callback(value) {
                            return Number(value).toFixed(0);
                        }
                    }
                },
                macd: {
                    position: 'right',
                    display: false,
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        callback(value) {
                            return Number(value).toFixed(2);
                        }
                    }
                },
                volume: {
                    display: false,
                    min: 0,
                    max: maxVolume * 4,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });

    state.chart.$marketChart = state;
    bindMarketChartCanvasInteractions(state);
    applyMarketChartVisibility(state);
}

function buildMarketChartDatasets(rows) {
    const closeValues = rows.map(row => row.close);
    const barColors = rows.map(row => row.close >= row.open ? 'rgba(46, 213, 115, 0.55)' : 'rgba(255, 71, 87, 0.55)');
    const volumeColors = rows.map(row => row.close >= row.open ? 'rgba(46, 213, 115, 0.18)' : 'rgba(255, 71, 87, 0.18)');

    return [
        {
            label: 'Close',
            data: closeValues,
            borderColor: 'rgba(0, 212, 255, 0)',
            backgroundColor: 'rgba(0, 212, 255, 0)',
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 0,
            marketRole: 'priceHover',
            tooltipKey: 'close',
            tooltipHidden: true,
            order: 0
        },
        {
            label: 'Close',
            data: closeValues,
            borderColor: '#00d4ff',
            backgroundColor: 'rgba(0, 212, 255, 0.12)',
            borderWidth: 2.5,
            pointRadius: 2.4,
            pointHoverRadius: 5,
            tension: 0.28,
            marketRole: 'priceLine',
            tooltipKey: 'close',
            order: 2
        },
        {
            type: 'bar',
            label: 'Close',
            data: closeValues,
            backgroundColor: barColors,
            borderColor: barColors,
            borderWidth: 1,
            marketRole: 'priceBars',
            tooltipKey: 'close',
            hidden: true,
            order: 3
        },
        {
            type: 'bar',
            label: 'Volume',
            data: rows.map(row => row.volume),
            yAxisID: 'volume',
            backgroundColor: volumeColors,
            borderColor: 'rgba(168, 180, 198, 0.18)',
            borderWidth: 1,
            marketRole: 'volume',
            tooltipKey: 'volume',
            order: 8
        },
        lineDataset('EMA(50)', rows.map(row => row.ema), '#ffa502', 'ema', 'ema'),
        lineDataset('SMA(20)', rows.map(row => row.sma), '#8fdbff', 'sma', 'sma'),
        lineDataset('RSI(14)', rows.map(row => row.rsi), '#d8b4fe', 'rsi', 'rsi', 'rsi'),
        lineDataset('MACD', rows.map(row => row.macd), '#2ed573', 'macd', 'macd', 'macd'),
        lineDataset('MACD Signal', rows.map(row => row.macdSignal), '#ffbf69', 'macd', 'macdSignal', 'macd'),
        {
            type: 'bar',
            label: 'MACD Histogram',
            data: rows.map(row => row.macdHistogram),
            yAxisID: 'macd',
            backgroundColor: rows.map(row => (row.macdHistogram || 0) >= 0 ? 'rgba(46, 213, 115, 0.42)' : 'rgba(255, 71, 87, 0.42)'),
            borderWidth: 0,
            indicatorKey: 'macd',
            tooltipKey: 'macdHistogram',
            hidden: true,
            order: 7
        },
        lineDataset('Bollinger Upper', rows.map(row => row.bollingerUpper), '#4dabf7', 'bollinger', 'bollingerUpper'),
        lineDataset('Bollinger Mid', rows.map(row => row.bollingerMiddle), 'rgba(77, 171, 247, 0.5)', 'bollinger', 'bollingerMiddle'),
        lineDataset('Bollinger Lower', rows.map(row => row.bollingerLower), '#4dabf7', 'bollinger', 'bollingerLower')
    ];
}

function lineDataset(label, data, color, indicatorKey, tooltipKey, axisId) {
    return {
        label: label,
        data: data,
        yAxisID: axisId || 'y',
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.25,
        spanGaps: true,
        indicatorKey: indicatorKey,
        tooltipKey: tooltipKey,
        hidden: indicatorKey !== 'ema',
        order: 4
    };
}

function applyMarketChartVisibility(state) {
    if (!state.chart) {
        return;
    }

    state.chart.data.datasets.forEach(dataset => {
        if (dataset.marketRole === 'priceLine') {
            dataset.hidden = state.view !== 'line';
        } else if (dataset.marketRole === 'priceBars') {
            dataset.hidden = state.view !== 'bar';
        } else if (dataset.marketRole === 'priceHover' || dataset.marketRole === 'volume') {
            dataset.hidden = false;
        } else if (dataset.indicatorKey) {
            dataset.hidden = !state.indicators[dataset.indicatorKey];
        }
    });

    state.chart.options.scales.rsi.display = Boolean(state.indicators.rsi);
    state.chart.options.scales.macd.display = Boolean(state.indicators.macd);
    state.chart.$marketChart = state;
    state.chart.update();
    updateMarketChartLegend(state);
}

function updateMarketChartLegend(state) {
    state.card.querySelectorAll('[data-legend-key]').forEach(item => {
        const key = item.dataset.legendKey;
        const active = key === 'price' || key === 'volume' || Boolean(state.indicators[key]);
        item.classList.toggle('active', active);
    });
}

function bindMarketChartCanvasInteractions(state) {
    const canvas = state.chart.canvas;

    canvas.addEventListener('wheel', event => {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const centerRatio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        zoomMarketChart(state, event.deltaY > 0 ? 1.22 : 0.82, centerRatio);
    }, {passive: false});

    canvas.addEventListener('pointerdown', event => {
        if (!state.chart.chartArea) {
            return;
        }
        canvas.setPointerCapture(event.pointerId);
        state.dragState = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startStart: state.visibleStart,
            startEnd: state.visibleEnd
        };
    });

    canvas.addEventListener('pointermove', event => {
        if (!state.dragState || state.dragState.pointerId !== event.pointerId) {
            return;
        }
        const span = state.dragState.startEnd - state.dragState.startStart;
        const chartWidth = Math.max(state.chart.chartArea.right - state.chart.chartArea.left, 1);
        const deltaIndex = -((event.clientX - state.dragState.startX) / chartWidth) * span;
        setMarketChartRange(state, state.dragState.startStart + deltaIndex, state.dragState.startEnd + deltaIndex);
    });

    canvas.addEventListener('pointerup', event => {
        if (state.dragState && state.dragState.pointerId === event.pointerId) {
            state.dragState = null;
        }
    });

    canvas.addEventListener('keydown', event => {
        if (event.key === '+' || event.key === '=') {
            event.preventDefault();
            zoomMarketChart(state, 0.72);
        } else if (event.key === '-' || event.key === '_') {
            event.preventDefault();
            zoomMarketChart(state, 1.35);
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            panMarketChart(state, -0.12);
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            panMarketChart(state, 0.12);
        } else if (event.key === 'Home') {
            event.preventDefault();
            resetMarketChartZoom(state);
        }
    });
}

function zoomMarketChart(state, factor, centerRatio) {
    if (!state.chart || !state.payload) {
        return;
    }

    const maxIndex = state.payload.rows.length - 1;
    const currentSpan = Math.max(state.visibleEnd - state.visibleStart, 1);
    const newSpan = Math.max(8, Math.min(maxIndex, currentSpan * factor));
    const ratio = centerRatio === undefined ? 0.5 : centerRatio;
    const center = state.visibleStart + currentSpan * ratio;
    setMarketChartRange(state, center - newSpan * ratio, center + newSpan * (1 - ratio));
}

function panMarketChart(state, ratio) {
    const span = state.visibleEnd - state.visibleStart;
    const offset = span * ratio;
    setMarketChartRange(state, state.visibleStart + offset, state.visibleEnd + offset);
}

function resetMarketChartZoom(state) {
    if (!state.payload) {
        return;
    }
    setMarketChartRange(state, 0, state.payload.rows.length - 1);
}

function setMarketChartRange(state, start, end) {
    const maxIndex = state.payload.rows.length - 1;
    const span = Math.max(end - start, 1);
    let nextStart = start;
    let nextEnd = end;

    if (nextStart < 0) {
        nextStart = 0;
        nextEnd = Math.min(span, maxIndex);
    }
    if (nextEnd > maxIndex) {
        nextEnd = maxIndex;
        nextStart = Math.max(0, maxIndex - span);
    }

    state.visibleStart = Math.max(0, nextStart);
    state.visibleEnd = Math.min(maxIndex, nextEnd);
    state.chart.options.scales.x.min = Math.round(state.visibleStart);
    state.chart.options.scales.x.max = Math.round(state.visibleEnd);
    state.chart.update('none');
}

function refreshMarketChart(state, options) {
    const card = state.card;
    const urlText = card.dataset.refreshUrl;
    if (!urlText) {
        return;
    }

    const url = new URL(urlText, window.location.origin);
    const timeframe = options && options.timeframe;
    if (timeframe) {
        url.searchParams.set('timeframe', timeframe);
    }
    url.searchParams.set('refresh', options && options.live ? '1' : '0');

    setRefreshLoading(card, true);
    fetch(url.toString(), {
        credentials: 'same-origin',
        headers: {
            'HX-Request': 'true'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Chart refresh failed (${response.status}).`);
            }
            return response.text();
        })
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const nextCard = doc.querySelector('[data-market-chart]');
            if (!nextCard) {
                throw new Error('Chart response did not include a chart fragment.');
            }

            nextCard.dataset.persistAutoRefresh = state.autoRefresh ? '1' : '0';
            nextCard.dataset.persistInterval = String(state.refreshInterval);
            disposeMarketChart(card);
            card.replaceWith(nextCard);
            initializeMarketCharts(nextCard);
            if (typeof refreshLucideIcons === 'function') {
                refreshLucideIcons();
            }
            setupTooltips();
        })
        .catch(error => {
            console.error(error);
            showMarketChartError(card, error.message);
        })
        .finally(() => setRefreshLoading(card, false));
}

function scheduleMarketChartRefresh(state) {
    clearTimeout(state.refreshTimer);
    clearInterval(state.countdownTimer);

    if (!state.autoRefresh) {
        updateCountdownLabel(state, null);
        return;
    }

    const intervalMs = Math.max(state.refreshInterval || 45, 5) * 1000;
    state.nextRefreshAt = Date.now() + intervalMs;
    state.countdownTimer = setInterval(() => updateCountdownLabel(state, state.nextRefreshAt), 1000);
    updateCountdownLabel(state, state.nextRefreshAt);
    state.refreshTimer = setTimeout(() => refreshMarketChart(state, {live: true}), intervalMs);
}

function updateCountdownLabel(state, nextRefreshAt) {
    const label = state.card.querySelector('[data-chart-countdown]');
    if (!label) {
        return;
    }
    if (!nextRefreshAt) {
        label.textContent = 'Auto refresh off';
        return;
    }
    const seconds = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000));
    label.textContent = `Auto refresh in ${seconds}s`;
}

function setRefreshLoading(card, isLoading) {
    card.querySelectorAll('[data-chart-refresh]').forEach(button => {
        button.disabled = isLoading;
        button.classList.toggle('is-loading', isLoading);
    });
}

function showMarketChartError(card, message) {
    let alert = card.querySelector('[data-chart-error]');
    if (!alert) {
        alert = document.createElement('div');
        alert.className = 'alert alert-warning d-flex flex-wrap justify-content-between align-items-center gap-2 mt-3 mb-0';
        alert.setAttribute('role', 'alert');
        alert.dataset.chartError = 'true';
        const body = card.querySelector('.card-body');
        if (body) {
            body.appendChild(alert);
        }
    }
    alert.innerHTML = `<span>${escapeHtml(message)}</span><button class="btn btn-sm btn-outline-warning" type="button" data-chart-refresh><i data-lucide="refresh-cw"></i> Retry</button>`;
    const state = card._marketChartState;
    const retry = alert.querySelector('[data-chart-refresh]');
    if (state && retry) {
        retry.addEventListener('click', () => refreshMarketChart(state, {live: true}));
    }
    if (typeof refreshLucideIcons === 'function') {
        refreshLucideIcons();
    }
}

function updateMarketChartStatus(state) {
    if (!state.payload || !state.payload.rows.length) {
        return;
    }
    const latest = state.payload.rows[state.payload.rows.length - 1];
    const momentum = state.card.querySelector('[data-chart-momentum]');
    if (momentum) {
        momentum.textContent = `Momentum ${formatSignedNumber(latest.momentum)} | Velocity ${formatPercentPoints(latest.velocity)}`;
    }
}

function setGroupedButtonActive(buttons, activeButton) {
    buttons.forEach(button => {
        const isActive = button === activeButton;
        button.classList.toggle('active', isActive);
        button.classList.toggle('btn-primary', isActive);
        button.classList.toggle('btn-outline-secondary', !isActive);
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
}

function setToggleButtonState(button, active) {
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
}

function rowFromTooltip(item, rows) {
    if (!item) {
        return null;
    }
    return rows[item.dataIndex] || null;
}

function marketTooltipLabel(context, currency) {
    const value = context.parsed.y;
    if (value === null || value === undefined) {
        return null;
    }

    switch (context.dataset.tooltipKey) {
        case 'close':
            return `Close: ${formatCurrency(value, currency)}`;
        case 'ema':
            return `EMA(50): ${formatCurrency(value, currency)}`;
        case 'sma':
            return `SMA(20): ${formatCurrency(value, currency)}`;
        case 'rsi':
            return `RSI(14): ${Number(value).toFixed(2)}`;
        case 'macd':
            return `MACD: ${formatSignedNumber(value)}`;
        case 'macdSignal':
            return `MACD signal: ${formatSignedNumber(value)}`;
        case 'macdHistogram':
            return `MACD hist: ${formatSignedNumber(value)}`;
        case 'bollingerUpper':
            return `BB upper: ${formatCurrency(value, currency)}`;
        case 'bollingerMiddle':
            return `BB mid: ${formatCurrency(value, currency)}`;
        case 'bollingerLower':
            return `BB lower: ${formatCurrency(value, currency)}`;
        case 'volume':
            return `Volume: ${formatVolume(value)}`;
        default:
            return `${context.dataset.label}: ${formatChartNumber(value)}`;
    }
}

function compactTimestamp(timestampText) {
    const date = new Date(timestampText);
    if (Number.isNaN(date.getTime())) {
        return '';
    }
    const sameYear = date.getFullYear() === new Date().getFullYear();
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        hour: sameYear ? 'numeric' : undefined,
        minute: sameYear ? '2-digit' : undefined
    }).format(date);
}

function formatAxisCurrency(value, currency) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency || 'USD',
        notation: Math.abs(value) >= 100000 ? 'compact' : 'standard',
        maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2
    }).format(value);
}

function formatPercentPoints(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'n/a';
    }
    const number = Number(value);
    const sign = number > 0 ? '+' : '';
    return `${sign}${number.toFixed(2)}%`;
}

function formatSignedNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'n/a';
    }
    const number = Number(value);
    const sign = number > 0 ? '+' : '';
    return `${sign}${number.toFixed(2)}`;
}

function formatChartNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return 'n/a';
    }
    return Number(value).toFixed(2);
}

function formatVolume(value) {
    return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(Number(value) || 0);
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function formatCurrency(value, currency) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency || 'USD',
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
