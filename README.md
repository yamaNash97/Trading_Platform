# Automated Stock Trading Strategy Simulator

Educational Django trading simulator for market data, configurable strategies, historical backtesting, paper orders, and portfolio dashboards.

## Tech Stack

- Django 6
- PostgreSQL in configured environments
- SQLite fallback for local demos
- Bootstrap templates
- Alpha Vantage integration hook

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, create an account, add a stock, create a strategy, run a backtest, then place paper trades.

## PostgreSQL Configuration

Set the `POSTGRES_*` environment variables from `.env.example`. If `POSTGRES_DB` is not set, Django uses local SQLite so the simulator can run immediately for demos and tests.

## Market Data

The app can seed deterministic sample OHLCV data without network access. To import daily Alpha Vantage data, set `ALPHA_VANTAGE_API_KEY` and use the stock detail refresh action.

## Apps

- `accounts`: signup and profiles
- `market_data`: stocks and OHLCV prices
- `strategies`: moving average, RSI, and combined strategy configuration
- `backtesting`: long-only simulation engine and performance reports
- `paper_trading`: virtual account, orders, transactions
- `portfolio`: dashboard and holdings
