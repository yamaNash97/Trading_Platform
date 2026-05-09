# Dark Theme - Quick Reference Guide

## 🎨 Color Classes

### Text Colors
```html
<p class="text-accent-primary">Cyan text</p>
<p class="text-accent-secondary">Green text</p>
<p class="text-gain">Green (gains)</p>
<p class="text-loss">Red (losses)</p>
```

### Background Classes
```html
<div class="bg-card">Card background</div>
<div class="border-accent">Accent border</div>
<div class="shadow-glow">Glowing shadow</div>
```

---

## 🔘 Button Styles

### Primary Button
```html
<button class="btn btn-primary">Primary Action</button>
```

### Success Button
```html
<button class="btn btn-success">Confirm Trade</button>
```

### Danger Button
```html
<button class="btn btn-danger">Sell / Delete</button>
```

### Outline Button
```html
<button class="btn btn-outline-primary">Secondary Action</button>
```

---

## 💳 Card Components

### Standard Card
```html
<div class="card">
    <div class="card-header">
        <h5 class="card-title">Card Title</h5>
    </div>
    <div class="card-body">
        <p class="card-text">Content here</p>
    </div>
</div>
```

### Trading Card
```html
<div class="trading-card">
    <h4>AAPL Performance</h4>
    <div class="price-display">$175.50</div>
    <span class="percentage-change positive">+5.2%</span>
</div>
```

---

## 🏷️ Badges

### Success Badge
```html
<span class="badge bg-success">LONG</span>
```

### Danger Badge
```html
<span class="badge bg-danger">SHORT</span>
```

### Warning Badge
```html
<span class="badge bg-warning">PENDING</span>
```

### Info Badge
```html
<span class="badge bg-info">COMPLETED</span>
```

---

## ⚠️ Alerts

### Success Alert
```html
<div class="alert alert-success">
    <i class="fas fa-check-circle"></i>
    Trade executed successfully!
</div>
```

### Danger Alert
```html
<div class="alert alert-danger">
    <i class="fas fa-exclamation-circle"></i>
    Insufficient funds!
</div>
```

### Warning Alert
```html
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle"></i>
    High volatility detected
</div>
```

### Info Alert
```html
<div class="alert alert-info">
    <i class="fas fa-info-circle"></i>
    Market update available
</div>
```

---

## 📊 Tables

### Dark Table
```html
<table class="table table-dark">
    <thead>
        <tr>
            <th>Column 1</th>
            <th>Column 2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Data</td>
            <td class="gain">+2.5%</td>
        </tr>
    </tbody>
</table>
```

---

## 📈 Forms

### Form Input
```html
<div class="mb-3">
    <label for="inputEmail" class="form-label">Email</label>
    <input type="email" class="form-control" id="inputEmail" placeholder="Enter email">
</div>
```

### Form Select
```html
<div class="mb-3">
    <label for="selectStrategy" class="form-label">Strategy</label>
    <select class="form-select" id="selectStrategy">
        <option>Choose strategy...</option>
        <option value="ma">Moving Average</option>
        <option value="rsi">RSI</option>
    </select>
</div>
```

### Form Validation
```html
<form class="needs-validation">
    <input class="form-control" required>
    <div class="invalid-feedback">
        This field is required
    </div>
</form>
```

---

## 🎬 Animation Classes

### Slide In Animation
```html
<div class="card animate-slide">Slides in on page load</div>
```

### Glow Animation
```html
<button class="btn btn-primary animate-glow">Glowing button</button>
```

### Pulse Animation
```html
<div class="animate-pulse">Pulsing element</div>
```

---

## 🗂️ Layout Components

### Container
```html
<div class="container-fluid px-4">
    <h1>Page Title</h1>
    <!-- Content -->
</div>
```

### Grid Layout
```html
<div class="row">
    <div class="col-md-6">Half width on desktop</div>
    <div class="col-md-6">Half width on desktop</div>
</div>
```

### Spacer/Margin
```html
<!-- mt-4 = margin-top: 1.5rem -->
<div class="mt-4 mb-3 px-2">Spaced content</div>
```

---

## 🎯 Trading-Specific Classes

### Price Display
```html
<div class="price-display">$125.50</div>
```

### Percentage Change
```html
<!-- Automatic coloring -->
<span class="percentage-change positive">+15.5%</span>
<span class="percentage-change negative">-8.2%</span>
```

### Gain/Loss Text
```html
<span class="gain">+$500</span>
<span class="loss">-$300</span>
```

---

## 📱 Responsive Classes

### Responsive Text
```html
<!-- Hide on mobile, show on tablet+ -->
<div class="d-none d-md-block">Desktop only</div>

<!-- Show on mobile only -->
<div class="d-md-none">Mobile only</div>
```

### Responsive Columns
```html
<div class="row">
    <!-- Full width on mobile, half on tablet+, third on desktop -->
    <div class="col-12 col-md-6 col-lg-4">Column</div>
</div>
```

---

## 🌐 Navigation

### Navbar
```html
<nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container-fluid">
        <a class="navbar-brand" href="#"><i class="fas fa-chart-line"></i> Brand</a>
        <button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#nav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="nav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item">
                    <a class="nav-link active" href="#">Link</a>
                </li>
            </ul>
        </div>
    </div>
</nav>
```

---

## 💻 CSS Variables

Use these variables in your own CSS:

```css
/* Colors */
var(--primary-dark)        /* Main background: #0f1419 */
var(--secondary-dark)      /* Secondary bg: #1a1f2e */
var(--accent-primary)      /* Cyan: #00d4ff */
var(--accent-secondary)    /* Green: #00f0a0 */
var(--accent-success)      /* Green: #2ed573 */
var(--accent-danger)       /* Red: #ff4757 */

/* Text */
var(--text-primary)        /* Main text: #e8eef5 */
var(--text-secondary)      /* Secondary text: #a8b4c6 */
var(--text-tertiary)       /* Tertiary text: #7a8494 */

/* Effects */
var(--shadow-md)           /* Medium shadow */
var(--shadow-lg)           /* Large shadow */
var(--shadow-glow)         /* Glow effect */
var(--transition-smooth)   /* Smooth animation */
var(--transition-fast)     /* Fast animation */

/* Gradients */
var(--gradient-gain)       /* Green gradient */
var(--gradient-loss)       /* Red gradient */
```

---

## 🔗 External Resources

### Icons (Font Awesome)
```html
<i class="fas fa-chart-line"></i>      <!-- Chart icon -->
<i class="fas fa-coins"></i>            <!-- Coins icon -->
<i class="fas fa-rocket"></i>           <!-- Rocket icon -->
<i class="fas fa-history"></i>          <!-- History icon -->
<i class="fas fa-exchange-alt"></i>     <!-- Exchange icon -->
<i class="fas fa-wallet"></i>           <!-- Wallet icon -->
<i class="fas fa-check-circle"></i>     <!-- Success icon -->
<i class="fas fa-exclamation-circle"></i> <!-- Error icon -->
```

### CDN Links (included in base template)
```html
<!-- Bootstrap 5 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- Font Awesome -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

---

## 📚 Component Examples

### Dashboard Card Grid
```html
<div class="row g-4">
    <div class="col-md-3">
        <div class="trading-card">
            <small class="text-secondary">Portfolio Value</small>
            <div class="price-display">$50,250</div>
            <span class="percentage-change positive">+12.5%</span>
        </div>
    </div>
    <!-- More cards -->
</div>
```

### Trade Order Form
```html
<div class="card">
    <div class="card-header">
        <h5>Place Order</h5>
    </div>
    <div class="card-body">
        <div class="mb-3">
            <label class="form-label">Stock Symbol</label>
            <input type="text" class="form-control">
        </div>
        <div class="mb-3">
            <label class="form-label">Quantity</label>
            <input type="number" class="form-control">
        </div>
        <button class="btn btn-success">Place Order</button>
    </div>
</div>
```

### Performance Chart
```html
<div class="card">
    <div class="card-header">
        <h5>Portfolio Performance</h5>
    </div>
    <div class="card-body">
        <canvas id="performanceChart"></canvas>
    </div>
</div>

<script>
    const ctx = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            datasets: [{
                label: 'Portfolio Value',
                data: [45000, 47000, 50000, 52000, 55000],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                tension: 0.4
            }]
        }
    });
</script>
```

---

## ✅ Best Practices

1. **Use semantic HTML**: Use `<button>` for actions, `<a>` for navigation
2. **Combine classes**: Mix utility classes for spacing/alignment
3. **Color meanings**: Keep gain=green, loss=red for consistency
4. **Icons**: Use Font Awesome for visual clarity
5. **Responsive**: Always design mobile-first, then enhance
6. **Performance**: Minimize custom CSS, use theme variables
7. **Accessibility**: Include `aria-labels` and proper `alt` attributes

---

## 📖 Common Patterns

### Status Indicator
```html
<div class="d-flex align-items-center gap-2">
    <span class="badge bg-success">ACTIVE</span>
    <span>Strategy Name</span>
</div>
```

### Price Ticker
```html
<div>
    <span class="price-display">$125.50</span>
    <small class="text-secondary ms-2">+2.5% today</small>
</div>
```

### Card with Metric
```html
<div class="trading-card">
    <small class="text-secondary">Metric Name</small>
    <div class="price-display mt-2">123.45</div>
    <span class="percentage-change positive mt-2 d-block">↑ 5.2%</span>
</div>
```

---

Need more examples? Check `IMPLEMENTATION_GUIDE.md` for detailed documentation!
