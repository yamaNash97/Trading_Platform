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
    findMarketChartCards(event.target).forEach(card => setRefreshLoading(card, false));
});

document.body.addEventListener('htmx:beforeSwap', function(event) {
    disposeMarketCharts(event.detail.target);
});

document.body.addEventListener('htmx:beforeRequest', function(event) {
    const card = closestMarketChartCard(event.detail && event.detail.elt);
    if (card) {
        setRefreshLoading(card, true);
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    const card = closestMarketChartCard(event.detail && event.detail.elt);
    if (card && !(event.detail && event.detail.successful)) {
        setRefreshLoading(card, false);
    }
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

function addGlowEffect() {
    const cards = document.querySelectorAll('.card, .btn-primary');
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

function setupTooltips() {
    if (!window.bootstrap || !window.bootstrap.Tooltip) {
        return;
    }

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new window.bootstrap.Tooltip(tooltipTriggerEl);
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
const MARKET_CHART_REFRESH_SECONDS = 300;
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

function closestMarketChartCard(element) {
    if (!element || !element.closest) {
        return null;
    }
    return element.closest('[data-market-chart]');
}

function setupMarketChartCard(card) {
    if (card.dataset.chartInitialized === 'true') {
        return;
    }

    card.dataset.chartInitialized = 'true';
    const payload = readMarketChartPayload(card);
    const state = {
        card: card,
        payload: payload,
        chart: null,
        indicators: {
            ema: true,
            rsi: false
        },
        visibleStart: 0,
        visibleEnd: payload ? Math.max(payload.rows.length - 1, 0) : 0,
        refreshTimer: null,
        countdownTimer: null,
        nextRefreshAt: null,
        dragState: null,
        crosshair: {
            visible: false,
            x: 0,
            y: 0
        },
        crosshairFrame: null
    };

    card._marketChartState = state;
    marketChartRegistry.set(card.id, state);
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
    if (state.crosshairFrame) {
        cancelAnimationFrame(state.crosshairFrame);
    }
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
            const marketState = chart.$marketChart;
            if (!marketState || !marketState.crosshair || !marketState.crosshair.visible) {
                return;
            }

            const {ctx, chartArea} = chart;
            const x = marketState.crosshair.x;
            const y = marketState.crosshair.y;
            if (x < chartArea.left || x > chartArea.right || y < chartArea.top || y > chartArea.bottom) {
                return;
            }

            ctx.save();
            ctx.strokeStyle = 'rgba(100, 150, 200, 0.3)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, chartArea.top);
            ctx.lineTo(x, chartArea.bottom);
            ctx.moveTo(chartArea.left, y);
            ctx.lineTo(chartArea.right, y);
            ctx.stroke();

            const yScale = chart.scales.y;
            if (yScale) {
                const currency = (marketState.payload && marketState.payload.currency) || 'USD';
                const label = formatCurrency(yScale.getValueForPixel(y), currency);
                drawCrosshairValueLabel(ctx, chartArea, y, label);
            }

            ctx.restore();
        }
    });

    marketChartPluginsRegistered = true;
}

function drawCrosshairValueLabel(ctx, chartArea, y, label) {
    const paddingX = 7;
    const paddingY = 4;
    const radius = 5;
    ctx.font = '12px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textBaseline = 'middle';

    const textWidth = ctx.measureText(label).width;
    const width = textWidth + paddingX * 2;
    const height = 22;
    const x = chartArea.right - width - 6;
    const labelY = Math.max(chartArea.top + height / 2, Math.min(chartArea.bottom - height / 2, y));
    const top = labelY - height / 2;

    ctx.fillStyle = 'rgba(0, 31, 32, 0.92)';
    ctx.strokeStyle = 'rgba(100, 150, 200, 0.45)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x + radius, top);
    ctx.lineTo(x + width - radius, top);
    ctx.quadraticCurveTo(x + width, top, x + width, top + radius);
    ctx.lineTo(x + width, top + height - radius);
    ctx.quadraticCurveTo(x + width, top + height, x + width - radius, top + height);
    ctx.lineTo(x + radius, top + height);
    ctx.quadraticCurveTo(x, top + height, x, top + height - radius);
    ctx.lineTo(x, top + radius);
    ctx.quadraticCurveTo(x, top, x + radius, top);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#e8eef5';
    ctx.fillText(label, x + paddingX, labelY);
}

function bindMarketChartControls(state) {
    const card = state.card;

    card.querySelectorAll('[data-chart-toggle]').forEach(button => {
        button.addEventListener('click', () => {
            runMarketChartLocalUpdate(state, () => {
                const key = button.dataset.chartToggle;
                state.indicators[key] = !state.indicators[key];
                setToggleButtonState(button, state.indicators[key]);
                applyMarketChartVisibility(state);
            });
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

    card.querySelectorAll('[data-chart-export]').forEach(button => {
        button.addEventListener('click', () => exportMarketChart(state));
    });

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
        lineDataset('RSI(14)', rows.map(row => row.rsi), '#d8b4fe', 'rsi', 'rsi', 'rsi')
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
        if (dataset.marketRole === 'priceLine' || dataset.marketRole === 'priceHover' || dataset.marketRole === 'volume') {
            dataset.hidden = false;
        } else if (dataset.indicatorKey) {
            dataset.hidden = !state.indicators[dataset.indicatorKey];
        }
    });

    state.chart.options.scales.rsi.display = Boolean(state.indicators.rsi);
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
        updateMarketChartCrosshair(state, event);
        canvas.setPointerCapture(event.pointerId);
        state.dragState = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startStart: state.visibleStart,
            startEnd: state.visibleEnd
        };
    });

    canvas.addEventListener('pointermove', event => {
        updateMarketChartCrosshair(state, event);
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

    canvas.addEventListener('pointerleave', () => hideMarketChartCrosshair(state));
    canvas.addEventListener('pointercancel', () => hideMarketChartCrosshair(state));

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

function updateMarketChartCrosshair(state, event) {
    if (!state.chart || !state.chart.chartArea) {
        return;
    }

    const rect = state.chart.canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const area = state.chart.chartArea;
    const visible = x >= area.left && x <= area.right && y >= area.top && y <= area.bottom;

    state.crosshair.visible = visible;
    state.crosshair.x = x;
    state.crosshair.y = y;
    requestMarketChartDraw(state);
}

function hideMarketChartCrosshair(state) {
    if (!state.crosshair || !state.crosshair.visible) {
        return;
    }
    state.crosshair.visible = false;
    requestMarketChartDraw(state);
}

function requestMarketChartDraw(state) {
    if (!state.chart || state.crosshairFrame) {
        return;
    }
    state.crosshairFrame = requestAnimationFrame(() => {
        state.crosshairFrame = null;
        if (state.chart) {
            state.chart.draw();
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

    clearMarketChartRefreshTimers(state);

    const url = new URL(urlText, window.location.origin);
    const timeframe = options && options.timeframe;
    if (timeframe) {
        url.searchParams.set('timeframe', timeframe);
    }
    const liveRefreshEnabled = card.dataset.liveRefresh !== '0';
    url.searchParams.set('refresh', liveRefreshEnabled && options && options.live ? '1' : '0');

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
        .finally(() => {
            setRefreshLoading(card, false);
            if (card.isConnected && card._marketChartState === state) {
                scheduleMarketChartRefresh(state);
            }
        });
}

function clearMarketChartRefreshTimers(state) {
    clearTimeout(state.refreshTimer);
    clearInterval(state.countdownTimer);
    state.refreshTimer = null;
    state.countdownTimer = null;
}

function scheduleMarketChartRefresh(state) {
    clearMarketChartRefreshTimers(state);

    if (!state.card || !state.card.isConnected) {
        return;
    }
    if (state.card.dataset.liveRefresh === '0') {
        const label = state.card.querySelector('[data-chart-countdown]');
        if (label) {
            label.textContent = 'Historical data';
        }
        return;
    }

    const intervalMs = MARKET_CHART_REFRESH_SECONDS * 1000;
    state.nextRefreshAt = Date.now() + intervalMs;
    state.countdownTimer = setInterval(() => updateCountdownLabel(state), 1000);
    updateCountdownLabel(state);
    state.refreshTimer = setTimeout(() => refreshMarketChart(state, {live: true}), intervalMs);
}

function updateCountdownLabel(state) {
    const label = state.card.querySelector('[data-chart-countdown]');
    if (!label) {
        return;
    }
    const seconds = Math.max(0, Math.ceil((state.nextRefreshAt - Date.now()) / 1000));
    label.textContent = `Auto refresh in ${seconds}s`;
}

function runMarketChartLocalUpdate(state, updater) {
    if (!state || !state.card) {
        return;
    }

    setRefreshLoading(state.card, true);
    requestAnimationFrame(() => {
        try {
            updater();
        } finally {
            window.setTimeout(() => setRefreshLoading(state.card, false), 180);
        }
    });
}

function setRefreshLoading(card, isLoading) {
    if (!card) {
        return;
    }
    card.classList.toggle('is-chart-loading', isLoading);
    const overlay = card.querySelector('[data-chart-loading]');
    if (overlay) {
        overlay.setAttribute('aria-hidden', isLoading ? 'false' : 'true');
    }
    card.querySelectorAll('[data-chart-refresh]').forEach(button => {
        button.disabled = isLoading;
        button.classList.toggle('is-loading', isLoading);
    });
    card.querySelectorAll('[data-chart-export]').forEach(button => {
        button.disabled = isLoading;
    });
}

function exportMarketChart(state) {
    if (!state || !state.chart || !state.payload) {
        return;
    }

    const exportButton = state.card.querySelector('[data-chart-export]');
    if (exportButton) {
        exportButton.disabled = true;
    }

    const wasCrosshairVisible = state.crosshair && state.crosshair.visible;
    if (state.crosshair) {
        state.crosshair.visible = false;
        state.chart.draw();
    }

    try {
        const canvas = renderMarketChartExportCanvas(state);
        const filename = buildMarketChartExportFilename(state);
        if (canvas.toBlob) {
            canvas.toBlob(blob => {
                if (blob) {
                    downloadBlob(blob, filename);
                }
                if (exportButton) {
                    exportButton.disabled = false;
                }
            }, 'image/png');
        } else {
            downloadDataUrl(canvas.toDataURL('image/png'), filename);
            if (exportButton) {
                exportButton.disabled = false;
            }
        }
    } catch (error) {
        console.error('Could not export market chart.', error);
        showMarketChartError(state.card, 'Could not export chart image.');
        if (exportButton) {
            exportButton.disabled = false;
        }
    } finally {
        if (state.crosshair) {
            state.crosshair.visible = wasCrosshairVisible;
            state.chart.draw();
        }
    }
}

function renderMarketChartExportCanvas(state) {
    const width = 1200;
    const height = 600;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    const symbol = state.payload.symbol || 'Market';
    const exportedAt = new Date();
    const lastUpdated = state.payload.lastUpdatedLabel || '';

    ctx.fillStyle = '#001f20';
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = '#e8eef5';
    ctx.font = '700 24px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText(`${symbol} Price Chart`, 28, 38);

    ctx.fillStyle = '#a8b4c6';
    ctx.font = '13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`Exported ${exportedAt.toLocaleString()}`, width - 28, 28);
    if (lastUpdated) {
        ctx.fillText(`Last update ${lastUpdated}`, width - 28, 48);
    }
    ctx.textAlign = 'left';

    const legendBottom = drawMarketChartExportLegend(ctx, state, 28, 66, width - 56);
    const chartTop = Math.max(96, legendBottom + 16);
    const chartHeight = height - chartTop - 28;
    ctx.drawImage(state.chart.canvas, 28, chartTop, width - 56, chartHeight);

    ctx.strokeStyle = 'rgba(100, 150, 200, 0.24)';
    ctx.lineWidth = 1;
    ctx.strokeRect(28, chartTop, width - 56, chartHeight);

    return canvas;
}

function drawMarketChartExportLegend(ctx, state, x, y, maxWidth) {
    const items = buildMarketChartExportLegend(state);
    let cursorX = x;
    let cursorY = y;
    const rowHeight = 22;

    ctx.font = '13px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textBaseline = 'middle';

    items.forEach(item => {
        const textWidth = ctx.measureText(item.label).width;
        const itemWidth = textWidth + 32;
        if (cursorX > x && cursorX + itemWidth > x + maxWidth) {
            cursorX = x;
            cursorY += rowHeight;
        }

        ctx.fillStyle = item.color;
        ctx.beginPath();
        ctx.arc(cursorX + 6, cursorY, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#d7e1ec';
        ctx.fillText(item.label, cursorX + 16, cursorY);
        cursorX += itemWidth;
    });

    return cursorY;
}

function buildMarketChartExportLegend(state) {
    const seen = new Set();
    const items = [{
        label: 'Price',
        color: '#00d4ff'
    }];

    return items.concat(state.chart.data.datasets
        .filter(dataset => !dataset.hidden && !dataset.tooltipHidden && dataset.marketRole !== 'priceLine')
        .map(dataset => ({
            label: marketChartExportDatasetLabel(dataset),
            color: marketChartExportDatasetColor(dataset)
        })))
        .filter(item => {
            const key = `${item.label}:${item.color}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
}

function marketChartExportDatasetLabel(dataset) {
    if (dataset.marketRole === 'priceLine') {
        return 'Price';
    }
    if (dataset.marketRole === 'volume') {
        return 'Volume';
    }
    return dataset.label || 'Series';
}

function marketChartExportDatasetColor(dataset) {
    const color = dataset.borderColor || dataset.backgroundColor || '#e8eef5';
    return Array.isArray(color) ? color[0] : color;
}

function buildMarketChartExportFilename(state) {
    const symbol = String((state.payload && state.payload.symbol) || 'market').toLowerCase().replace(/[^a-z0-9_-]+/g, '-');
    const date = new Date().toISOString().slice(0, 10);
    return `chart-${symbol}-${date}.png`;
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    downloadDataUrl(url, filename);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadDataUrl(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
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
        case 'rsi':
            return `RSI(14): ${Number(value).toFixed(2)}`;
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
