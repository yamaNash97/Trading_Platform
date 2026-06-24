# Design and Implementation of an Automated Stock Trading Strategy Simulator Using Web Technologies (Trading Bot)

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

Set `DATABASE_URL` or the `POSTGRES_*` environment variables from `.env.example`. If neither `DATABASE_URL` nor `POSTGRES_DB` is set, Django uses local SQLite so the simulator can run immediately for demos and tests.

## Render Deployment

This repository includes `render.yaml` and `build.sh` for Render.

1. Push the project to GitHub.
2. In Render, create a new Blueprint from the repository, or create a Python Web Service manually.
3. Use these manual settings if you do not use the Blueprint:
   - Build Command: `bash build.sh`
   - Start Command: `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Create or attach a Render PostgreSQL database and set `DATABASE_URL` to its internal connection string.
5. Set environment variables:
   - `DJANGO_DEBUG=False`
   - `DJANGO_SECRET_KEY=<generated-secret>`
   - `DJANGO_ALLOWED_HOSTS=.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://*.onrender.com`
   - `ALPHA_VANTAGE_API_KEY=<optional-live-market-data-key>`

The project includes `.python-version` with Python 3.13 so Render uses a Django 6 compatible runtime. The free Render PostgreSQL plan is good for demos, but free databases expire after 30 days.
The migration command is part of the Start Command because Render's Pre-Deploy Command is not available on the free tier.

The Blueprint runs `ensure_superuser` during startup. Set
`DJANGO_SUPERUSER_PASSWORD` in Render before deploying if you want the
configured admin account to be created automatically.

### Replacing an expired free database

If deployment fails with `failed to resolve host 'dpg-...'`, the free Render
PostgreSQL database has probably expired or been deleted. Free databases expire
30 days after creation.

The database resource name in `render.yaml` is date-versioned so a Blueprint
sync can create a fresh database and update `DATABASE_URL` automatically:

1. Open the Blueprint in the Render Dashboard.
2. Sync the latest `render.yaml`.
3. Approve creation of the new database and redeployment of the web service.
4. Confirm the deploy log shows migrations completing before Gunicorn starts.

The replacement database is empty. To preserve data from an expired database,
upgrade that database to a paid instance during Render's 14-day grace period
instead, then keep `DATABASE_URL` connected to it.

To create a different admin user manually, use the Render Shell:

```bash
python manage.py createsuperuser
```

## Market Data

The app can seed deterministic sample OHLCV data without network access. To import daily Alpha Vantage data, set `ALPHA_VANTAGE_API_KEY` and use the stock detail refresh action.

## Apps

- `accounts`: signup and profiles
- `market_data`: stocks and OHLCV prices
- `strategies`: moving average, RSI, and combined strategy configuration
- `backtesting`: long-only simulation engine and performance reports
- `paper_trading`: virtual account, orders, transactions
- `portfolio`: dashboard and holdings
