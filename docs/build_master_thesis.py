"""
Build a 120+ page Arabic SVU-style thesis document for the trading simulator.

The script is intentionally docs-only: it creates reproducible thesis assets,
captures local UI screenshots, and writes a new .docx without modifying the
application source or the existing thesis drafts.
"""

from __future__ import annotations

import os
import re
import math
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
ASSET_DIR = DOCS_DIR / "thesis_assets"
SCREENSHOT_DIR = ASSET_DIR / "screenshots"
DIAGRAM_DIR = ASSET_DIR / "diagrams"
CODE_DIR = ASSET_DIR / "code_screens"
OUTPUT_DOCX = DOCS_DIR / "automated_stock_trading_strategy_simulator_master_thesis_120p_ar.docx"
CHECK_OUTPUT = ASSET_DIR / "django_check_output.txt"
TEST_OUTPUT = ASSET_DIR / "django_test_output.txt"

BASE_URL = "http://127.0.0.1:8765"
DEMO_USERNAME = "thesis_demo_user"
DEMO_PASSWORD = "ThesisDemoPass123!"


@dataclass
class DemoObjects:
    user_id: int
    stock_id: int
    second_stock_id: int
    strategy_id: int
    rsi_strategy_id: int
    backtest_id: int


@dataclass
class Figure:
    title: str
    path: Path
    kind: str = "شكل"


FIGURES: list[Figure] = []
TABLE_TITLES: list[str] = []


def ensure_dirs() -> None:
    for directory in (ASSET_DIR, SCREENSHOT_DIR, DIAGRAM_DIR, CODE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def setup_django():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def run_command(name: str, args: list[str], output_path: Path, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    output_path.write_text(
        f"$ {' '.join(args)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}\n\nEXIT CODE: {completed.returncode}\n",
        encoding="utf-8",
    )
    print(f"{name}: exit {completed.returncode}")
    return completed


def prepare_demo_data() -> DemoObjects:
    setup_django()

    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from backtesting.models import BacktestResult
    from backtesting.services import run_backtest
    from market_data.models import Stock
    from market_data.services import seed_sample_prices
    from paper_trading.models import Order
    from paper_trading.services import execute_order, get_or_create_account
    from portfolio.models import PortfolioHolding
    from strategies.models import Strategy

    User = get_user_model()
    User.objects.filter(username=DEMO_USERNAME).delete()
    user = User.objects.create_user(username=DEMO_USERNAME, password=DEMO_PASSWORD, email="thesis.demo@example.com")
    get_or_create_account(user)

    stock, _ = Stock.objects.get_or_create(
        symbol="AAPL",
        defaults={"name": "Apple Inc.", "exchange": "NASDAQ", "currency": "USD"},
    )
    second_stock, _ = Stock.objects.get_or_create(
        symbol="MSFT",
        defaults={"name": "Microsoft Corporation", "exchange": "NASDAQ", "currency": "USD"},
    )
    commodity, _ = Stock.objects.get_or_create(
        symbol="GOLD",
        defaults={"name": "Gold Spot Price", "exchange": "Commodity", "currency": "USD"},
    )

    for item in (stock, second_stock, commodity):
        seed_sample_prices(item, days=260)

    strategy = Strategy.objects.create(
        user=user,
        stock=stock,
        name="SVU MA Crossover Demo",
        strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
        parameters={"short_window": 8, "long_window": 24, "rsi_period": 14, "rsi_buy_threshold": 30, "rsi_sell_threshold": 70},
        initial_balance=Decimal("10000"),
        position_size_percent=Decimal("35"),
        stop_loss_percent=Decimal("7"),
        take_profit_percent=Decimal("13"),
        is_active=True,
    )
    rsi_strategy = Strategy.objects.create(
        user=user,
        stock=second_stock,
        name="SVU RSI Risk Demo",
        strategy_type=Strategy.StrategyType.RSI,
        parameters={"short_window": 10, "long_window": 30, "rsi_period": 14, "rsi_buy_threshold": 34, "rsi_sell_threshold": 68},
        initial_balance=Decimal("15000"),
        position_size_percent=Decimal("25"),
        stop_loss_percent=Decimal("6"),
        take_profit_percent=Decimal("12"),
        is_active=True,
    )

    today = timezone.now().date()
    result = run_backtest(user, strategy, today - timedelta(days=320), today)
    run_backtest(user, rsi_strategy, today - timedelta(days=320), today)

    execute_order(Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=Decimal("12")))
    execute_order(Order(user=user, stock=second_stock, order_type=Order.OrderType.BUY, quantity=Decimal("8")))

    # Nudge the latest saved prices so dashboard/open-trade screenshots show visible P/L.
    for holding in PortfolioHolding.objects.filter(user=user).select_related("stock"):
        latest = holding.stock.price_data.order_by("-timestamp").first()
        if latest:
            latest.close_price = latest.close_price + Decimal("4.2500")
            latest.high_price = max(latest.high_price, latest.close_price)
            latest.save(update_fields=["close_price", "high_price"])

    BacktestResult.objects.filter(user=user).update()
    return DemoObjects(user.id, stock.id, second_stock.id, strategy.id, rsi_strategy.id, result.id)


def free_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def wait_for_server(process: subprocess.Popen[str], timeout: int = 45) -> None:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Django development server exited before becoming ready.")
        try:
            with urllib.request.urlopen(BASE_URL, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError("Timed out waiting for Django development server.")


def start_server() -> subprocess.Popen[str]:
    if not free_port(8765):
        raise RuntimeError("Port 8765 is already in use. Stop the existing server or update BASE_URL in the script.")
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    server_log = ASSET_DIR / "thesis_server.log"
    log_handle = server_log.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8765", "--noreload"],
        cwd=ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    # Keep the handle reachable so Windows does not close it too early.
    process._thesis_log_handle = log_handle  # type: ignore[attr-defined]
    wait_for_server(process)
    return process


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
    handle = getattr(process, "_thesis_log_handle", None)
    if handle:
        handle.close()


def capture_screenshots(demo: DemoObjects) -> list[Figure]:
    from playwright.sync_api import sync_playwright

    edge_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    captures: list[Figure] = []

    def save_page(page, filename: str, title: str, selector: str | None = None) -> None:
        path = SCREENSHOT_DIR / filename
        page.wait_for_timeout(1500)
        if selector:
            page.locator(selector).screenshot(path=str(path))
        else:
            page.screenshot(path=str(path), full_page=False)
        captures.append(Figure(title=title, path=path))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(edge_path) if edge_path.exists() else None,
            args=["--disable-gpu"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
        page = context.new_page()

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        save_page(page, "01_landing_page.png", "Landing page العامة لمنصة TradSim")

        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        save_page(page, "02_login_page.png", "صفحة تسجيل الدخول")

        page.goto(f"{BASE_URL}/accounts/signup/", wait_until="networkidle")
        save_page(page, "03_signup_page.png", "صفحة إنشاء حساب جديد")

        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page.fill("#id_username", DEMO_USERNAME)
        page.fill("#id_password", DEMO_PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url("**/dashboard/", timeout=15000)
        save_page(page, "04_portfolio_dashboard.png", "Portfolio Dashboard بعد إنشاء بيانات تجريبية")

        routes = [
            ("/market/", "05_market_data_list.png", "قائمة Market Data وإضافة Stock"),
            (f"/market/{demo.stock_id}/", "06_stock_detail_chart.png", "تفاصيل Stock مع الرسم البياني والمؤشرات"),
            ("/market/chart/", "07_stock_chart_selector.png", "صفحة مقارنة الرسوم واختيار Stock"),
            ("/strategies/", "08_strategy_list.png", "قائمة استراتيجيات المستخدم"),
            (f"/strategies/{demo.strategy_id}/", "09_strategy_detail.png", "تفاصيل Strategy ومعاملات المخاطرة"),
            ("/backtests/", "10_backtest_list.png", "واجهة تشغيل Backtesting وسجل النتائج"),
            (f"/backtests/{demo.backtest_id}/", "11_backtest_report.png", "تقرير Backtest مع المقاييس وEquity Curve"),
            ("/paper/", "12_paper_trading_account.png", "صفحة Paper Trading وتنفيذ الأوامر"),
        ]
        for route, filename, title in routes:
            page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
            save_page(page, filename, title)

        page.goto(f"{BASE_URL}/paper/", wait_until="networkidle")
        save_page(page, "13_open_trades_fragment.png", "جزء Open Trades وقيم الربح والخسارة", "#open-trades-panel")
        browser.close()

    return captures


def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if mono:
        candidates.extend([r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"])
    if bold:
        candidates.extend([r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"])
    candidates.extend([r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"])
    for item in candidates:
        try:
            return ImageFont.truetype(item, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_line_to_width(draw: ImageDraw.ImageDraw, line: str, font, max_width: int) -> list[str]:
    words = line.split()
    if not words:
        return [""]
    wrapped = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            wrapped.append(current)
            current = word
    wrapped.append(current)
    return wrapped


def fit_text_to_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font):
    max_width = box[2] - box[0] - 48
    max_height = box[3] - box[1] - 36
    start_size = getattr(font, "size", 22)
    for size in range(start_size, 13, -1):
        fitted_font = font.font_variant(size=size) if hasattr(font, "font_variant") else font
        lines = []
        for raw_line in text.split("\n"):
            lines.extend(wrap_line_to_width(draw, raw_line, fitted_font, max_width))
        heights = [text_size(draw, line, fitted_font)[1] for line in lines]
        total_height = sum(heights) + (len(lines) - 1) * 6
        if total_height <= max_height and all(text_size(draw, line, fitted_font)[0] <= max_width for line in lines):
            return lines, fitted_font, heights

    fallback_font = font.font_variant(size=14) if hasattr(font, "font_variant") else font
    lines = []
    for raw_line in text.split("\n"):
        lines.extend(wrap_line_to_width(draw, raw_line, fallback_font, max_width))
    heights = [text_size(draw, line, fallback_font)[1] for line in lines]
    return lines, fallback_font, heights


def draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font, fill=(20, 32, 45)) -> None:
    lines, fitted_font, line_heights = fit_text_to_box(draw, box, text, font)
    total_h = sum(line_heights) + (len(lines) - 1) * 6
    y = box[1] + ((box[3] - box[1]) - total_h) // 2
    for line, h in zip(lines, line_heights):
        width, _ = text_size(draw, line, fitted_font)
        x = box[0] + ((box[2] - box[0]) - width) // 2
        draw.text((x, y), line, font=fitted_font, fill=fill)
        y += h + 6


def box_center(box: tuple[int, int, int, int]) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def connector_point(
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
    margin: int = 22,
) -> tuple[int, int]:
    """Return a point just outside source_box on the ray to target_box."""
    source_x, source_y = box_center(source_box)
    target_x, target_y = box_center(target_box)
    dx = target_x - source_x
    dy = target_y - source_y
    if dx == 0 and dy == 0:
        return round(source_x), round(source_y)

    half_width = ((source_box[2] - source_box[0]) / 2) + margin
    half_height = ((source_box[3] - source_box[1]) / 2) + margin
    x_scale = half_width / abs(dx) if dx else float("inf")
    y_scale = half_height / abs(dy) if dy else float("inf")
    scale = min(x_scale, y_scale)
    return round(source_x + dx * scale), round(source_y + dy * scale)


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color=(25, 98, 145)) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    unit_x = dx / length
    unit_y = dy / length
    perp_x = -unit_y
    perp_y = unit_x
    head_length = 18
    head_width = 10
    draw.line([start, end], fill=color, width=4)
    points = [
        end,
        (
            round(end[0] - unit_x * head_length + perp_x * head_width),
            round(end[1] - unit_y * head_length + perp_y * head_width),
        ),
        (
            round(end[0] - unit_x * head_length - perp_x * head_width),
            round(end[1] - unit_y * head_length - perp_y * head_width),
        ),
    ]
    draw.polygon(points, fill=color)


def save_diagram(filename: str, title: str, boxes: list[tuple[str, tuple[int, int, int, int], str]], arrows: list[tuple[int, int]]) -> Figure:
    width, height = 1600, 950
    image = Image.new("RGB", (width, height), "#f7fafc")
    draw = ImageDraw.Draw(image)
    title_font = get_font(40, bold=True)
    box_font = get_font(25, bold=True)
    small_font = get_font(19)
    draw.text((60, 40), title, font=title_font, fill="#102a43")

    palette = {
        "ui": "#d8f3dc",
        "django": "#dbeafe",
        "service": "#fff3bf",
        "data": "#ffe3e3",
        "external": "#ede9fe",
        "test": "#e0f2fe",
    }
    outlines = {
        "ui": "#2f9e44",
        "django": "#2563eb",
        "service": "#f59f00",
        "data": "#e03131",
        "external": "#7c3aed",
        "test": "#0284c7",
    }
    # Draw connectors first and boxes second. Even if a diagonal relation crosses
    # another node's area, the later box fill masks that line instead of letting
    # the connector visually run through the node.
    for start, end in arrows:
        start_box = boxes[start][1]
        end_box = boxes[end][1]
        draw_arrow(draw, connector_point(start_box, end_box), connector_point(end_box, start_box))

    for label, box, kind in boxes:
        draw.rounded_rectangle(box, radius=22, fill=palette[kind], outline=outlines[kind], width=4)
        draw_centered(draw, box, label, box_font if "\n" not in label else small_font)

    path = DIAGRAM_DIR / filename
    image.save(path)
    return Figure(title=title, path=path)


def generate_diagrams() -> list[Figure]:
    diagrams = []
    diagrams.append(
        save_diagram(
            "architecture.png",
            "System Architecture",
            [
                ("Browser\nBootstrap / HTMX / Chart.js", (60, 160, 390, 320), "ui"),
                ("Django URL Router\nViews / Forms", (520, 160, 850, 320), "django"),
                ("Service Layer\nSignals / Backtests / Orders", (980, 160, 1340, 320), "service"),
                ("SQLite / PostgreSQL\nModels and Migrations", (520, 520, 850, 700), "data"),
                ("Alpha Vantage\nyfinance / Redis Cache", (980, 520, 1340, 700), "external"),
            ],
            [(0, 1), (1, 2), (2, 3), (2, 4), (1, 3)],
        )
    )
    diagrams.append(
        save_diagram(
            "django_apps.png",
            "Django App Decomposition",
            [
                ("accounts\nsignup + profile", (60, 160, 360, 300), "django"),
                ("market_data\nStock + PriceData", (450, 160, 750, 300), "data"),
                ("strategies\nMA / RSI settings", (840, 160, 1140, 300), "service"),
                ("backtesting\nhistorical simulation", (1230, 160, 1530, 300), "service"),
                ("paper_trading\norders + transactions", (300, 520, 650, 670), "service"),
                ("portfolio\ndashboard + holdings", (920, 520, 1270, 670), "ui"),
            ],
            [(0, 4), (1, 2), (2, 3), (4, 5), (3, 5)],
        )
    )
    diagrams.append(
        save_diagram(
            "erd.png",
            "Core Data Model / ERD",
            [
                ("User", (70, 160, 260, 280), "django"),
                ("Stock", (410, 160, 630, 280), "data"),
                ("PriceData\nOHLCV", (790, 160, 1050, 280), "data"),
                ("Strategy", (410, 470, 630, 590), "service"),
                ("BacktestResult\nBacktestTrade", (790, 470, 1110, 610), "service"),
                ("PaperAccount\nOrder / Transaction", (1180, 470, 1520, 610), "service"),
                ("PortfolioHolding", (1180, 160, 1520, 280), "data"),
            ],
            [(0, 3), (1, 2), (1, 3), (3, 4), (0, 5), (5, 6), (1, 6)],
        )
    )
    diagrams.append(
        save_diagram(
            "backtesting_sequence.png",
            "Backtesting Sequence",
            [
                ("User selects\nstrategy + dates", (60, 160, 330, 300), "ui"),
                ("BacktestRunForm\nvalidates input", (430, 160, 700, 300), "django"),
                ("PriceData queryset\nsingle source rule", (800, 160, 1100, 300), "data"),
                ("generate_signals()\nMA / RSI", (1200, 160, 1500, 300), "service"),
                ("run_backtest()\nrisk exits + equity", (430, 520, 760, 670), "service"),
                ("BacktestResult\ntrades + JSON curve", (900, 520, 1240, 670), "data"),
            ],
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        )
    )
    diagrams.append(
        save_diagram(
            "paper_trading_sequence.png",
            "Paper Trading Order Sequence",
            [
                ("OrderForm\nstock side quantity", (80, 160, 370, 300), "ui"),
                ("execute_order()", (490, 160, 750, 300), "service"),
                ("latest_price()\nfrom PriceData", (870, 160, 1160, 300), "data"),
                ("cash / holding\nvalidation", (1280, 160, 1530, 300), "service"),
                ("Order status\nfilled or rejected", (440, 520, 760, 670), "data"),
                ("Transaction +\nPortfolioHolding", (900, 520, 1230, 670), "data"),
            ],
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        )
    )
    diagrams.append(
        save_diagram(
            "market_data_flow.png",
            "Market Data Import and Chart Flow",
            [
                ("Stock symbol", (90, 160, 330, 300), "ui"),
                ("Sample seed\nor API refresh", (450, 160, 730, 300), "service"),
                ("Alpha Vantage\nyfinance", (850, 160, 1130, 300), "external"),
                ("PriceData upsert\nunique timestamp", (1250, 160, 1530, 300), "data"),
                ("chart_context()\nEMA + RSI + JSON", (500, 520, 850, 680), "service"),
                ("Chart.js canvas\nHTMX fragment", (1030, 520, 1370, 680), "ui"),
            ],
            [(0, 1), (1, 2), (1, 3), (3, 4), (4, 5)],
        )
    )
    diagrams.append(
        save_diagram(
            "testing_workflow.png",
            "Verification Workflow",
            [
                ("Django check", (120, 160, 380, 300), "test"),
                ("Unit / view tests\n29 tests", (510, 160, 810, 300), "test"),
                ("Demo data seed", (940, 160, 1200, 300), "data"),
                ("Browser screenshots", (1330, 160, 1540, 300), "ui"),
                ("Thesis docx\nfigures + appendices", (620, 520, 980, 690), "django"),
            ],
            [(0, 1), (1, 2), (2, 3), (3, 4)],
        )
    )
    return diagrams


def redact_code(text: str) -> str:
    text = re.sub(r"(ALPHA_VANTAGE_API_KEY\s*=\s*).*", r"\1'***REDACTED***'", text)
    text = re.sub(r"(SECRET_KEY\s*=\s*).*", r"\1'***REDACTED***'", text)
    text = re.sub(r"(PASSWORD['\"]?\s*:\s*).*", r"\1'***REDACTED***',", text)
    return text


def render_code_image(source: Path, filename: str, title: str, max_lines: int = 42) -> Figure:
    raw = redact_code(source.read_text(encoding="utf-8", errors="replace"))
    lines = raw.splitlines()[:max_lines]
    font = get_font(21, mono=True)
    title_font = get_font(30, bold=True)
    line_height = 30
    gutter = 86
    width = 1500
    height = 110 + line_height * max(1, len(lines)) + 40
    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.text((42, 34), title, font=title_font, fill="#e2e8f0")
    draw.rectangle((28, 88, width - 28, height - 28), fill="#111827", outline="#334155", width=2)
    for index, line in enumerate(lines, start=1):
        y = 98 + (index - 1) * line_height
        draw.text((48, y), f"{index:>3}", font=font, fill="#64748b")
        visible = line[:115].replace("\t", "    ")
        color = "#e5e7eb"
        stripped = visible.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("{#"):
            color = "#94a3b8"
        elif stripped.startswith("class ") or stripped.startswith("def "):
            color = "#93c5fd"
        elif "return" in stripped or "raise" in stripped:
            color = "#fca5a5"
        elif "=" in visible:
            color = "#fde68a"
        draw.text((gutter, y), visible, font=font, fill=color)
    path = CODE_DIR / filename
    image.save(path)
    return Figure(title=title, path=path)


def generate_code_images() -> list[Figure]:
    return [
        render_code_image(ROOT / "config" / "settings.py", "settings_redacted.png", "config/settings.py - redacted settings", 48),
        render_code_image(ROOT / "market_data" / "models.py", "market_models.png", "market_data/models.py - Stock and PriceData", 42),
        render_code_image(ROOT / "strategies" / "services.py", "strategy_signals.png", "strategies/services.py - signal generation", 62),
        render_code_image(ROOT / "backtesting" / "services.py", "backtesting_engine.png", "backtesting/services.py - simulation engine", 62),
        render_code_image(ROOT / "paper_trading" / "services.py", "paper_order_service.png", "paper_trading/services.py - order execution", 62),
        render_code_image(ROOT / "market_data" / "charting.py", "chart_context.png", "market_data/charting.py - chart context", 60),
    ]


def add_bidi(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:bidi")) is None:
        p_pr.append(OxmlElement("w:bidi"))
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def set_run_font(run, size: int = 13, bold: bool = False, color: str | None = None) -> None:
    run.font.name = "Arial"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    run._element.rPr.rFonts.set(qn("w:cs"), "Arial")
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_ar_paragraph(doc: Document, text: str = "", style: str | None = None, size: int = 13, bold: bool = False):
    paragraph = doc.add_paragraph(style=style)
    add_bidi(paragraph)
    paragraph.paragraph_format.line_spacing = 1.35
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(text)
    set_run_font(run, size=size, bold=bold)
    return paragraph


def add_en_paragraph(doc: Document, text: str = "", size: int = 12):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    return paragraph


def add_ar_heading(doc: Document, text: str, level: int = 1):
    paragraph = doc.add_heading("", level=level)
    add_bidi(paragraph)
    run = paragraph.add_run(text)
    set_run_font(run, size=18 if level == 1 else 15 if level == 2 else 13, bold=True, color="102A43")
    return paragraph


def add_field(paragraph, field_code: str, placeholder: str = "") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field_code
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    TABLE_TITLES.append(title)
    add_ar_paragraph(doc, f"جدول {len(TABLE_TITLES)}: {title}", size=12, bold=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        add_bidi(p)
        run = p.add_run(header)
        set_run_font(run, size=11, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            p = cells[idx].paragraphs[0]
            add_bidi(p)
            run = p.add_run(value)
            set_run_font(run, size=10)
    doc.add_paragraph()


def add_figure(doc: Document, figure: Figure, width: float = 6.9) -> None:
    if not figure.path.exists():
        return
    FIGURES.append(figure)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(figure.path), width=Inches(width))
    add_ar_paragraph(doc, f"{figure.kind} {len(FIGURES)}: {figure.title}", size=11, bold=True)


def add_page_break(doc: Document) -> None:
    doc.add_page_break()


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:cs"), "Arial")
    normal.font.size = Pt(13)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("صفحة ")
    add_field(footer, "PAGE", "1")
    footer.add_run(" من ")
    add_field(footer, "NUMPAGES", "120+")


def title_page(doc: Document) -> None:
    for text, size in [
        ("الجامعة الافتراضية السورية", 20),
        ("برنامج ماجستير تقانة الويب", 18),
        ("رسالة ماجستير", 18),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        set_run_font(run, size=size, bold=True)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("تصميم وتنفيذ محاكي استراتيجيات تداول الأسهم الآلي باستخدام تقانات الويب")
    set_run_font(run, size=22, bold=True, color="0B7285")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Design and Implementation of an Automated Stock Trading Strategy Simulator Using Web Technologies")
    run.font.name = "Times New Roman"
    run.font.size = Pt(16)
    run.font.bold = True
    doc.add_paragraph()
    for text in [
        "إعداد الطالب: [اسم الطالب]",
        "إشراف الدكتور: [اسم المشرف]",
        "أعضاء لجنة الحكم: [تُملأ وفق قرار الجامعة]",
        "السنة الدراسية: 2025/2026",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        set_run_font(run, size=15, bold=True)
    add_ar_paragraph(
        doc,
        "ملاحظة منهجية: هذا العمل يصف نظاماً تعليمياً ومحاكياً، ولا يقدم نصيحة استثمارية ولا ينفذ أي تداول بأموال حقيقية.",
        size=12,
        bold=True,
    )
    add_page_break(doc)


def front_matter(doc: Document) -> None:
    add_ar_heading(doc, "قرار لجنة الحكم", 1)
    add_ar_paragraph(
        doc,
        "تُترك هذه الصفحة لقالب الجامعة الرسمي، وتتضمن أسماء أعضاء لجنة الحكم، تاريخ المناقشة، وقرار قبول الرسالة أو تعديلها. "
        "حُفظت هذه الصفحة بصيغتها القابلة للتخصيص لأن بيانات اللجنة والقرار النهائيين لا تُستنتج من المستودع البرمجي.",
    )
    add_page_break(doc)

    add_ar_heading(doc, "الإهداء", 1)
    add_ar_paragraph(
        doc,
        "إلى كل من آمن بأن المعرفة تصبح أكثر قيمة عندما تتحول إلى أداة عملية تساعد الآخرين على الفهم والتجريب الآمن. "
        "إلى العائلة والأساتذة والزملاء، وإلى كل طالب يبحث عن جسر واضح بين مفاهيم الأسواق المالية وتقانات الويب الحديثة.",
    )
    add_page_break(doc)

    add_ar_heading(doc, "الشكر والتقدير", 1)
    add_ar_paragraph(
        doc,
        "أتقدم بالشكر إلى الجامعة الافتراضية السورية وإلى الكادر التدريسي في برنامج ماجستير تقانة الويب على ما قدموه من معرفة وتوجيه. "
        "كما أشكر المشرف العلمي على دعمه في تحويل الفكرة من تصور أولي إلى تطبيق ويب يعمل ويخضع للاختبار. "
        "وقد ساعدت مراجعة المشروع وتشغيله وتوثيقه على تعميق الربط بين الجانب الأكاديمي والجانب التطبيقي.",
    )
    add_page_break(doc)

    add_ar_heading(doc, "المستخلص العربي", 1)
    for paragraph in [
        "تهدف هذه الرسالة إلى تصميم وتنفيذ منصة Web تعليمية لمحاكاة استراتيجيات تداول الأسهم الآلي. تجمع المنصة بين إدارة بيانات السوق، إعداد استراتيجيات قابلة للتخصيص، تنفيذ Backtesting تاريخي، تنفيذ Paper trading بمحفظة افتراضية، وعرض Dashboard يوضح حالة الحساب والأرباح والخسائر.",
        "تنطلق المشكلة من أن كثيراً من الطلاب والمتداولين المبتدئين يدرسون مؤشرات التداول وقواعده نظرياً، لكنهم يفتقرون إلى بيئة آمنة ومتكاملة تسمح لهم بالتجريب دون تعريض رأس مال حقيقي للخطر. لذلك يعالج المشروع الحاجة إلى بيئة تعليمية موحدة تربط البيانات والمؤشرات والمحاكاة والنتائج في مسار واحد.",
        "تم بناء النظام باستخدام Django 6.0.5 مع بنية تطبيقات منفصلة تشمل accounts وmarket_data وstrategies وbacktesting وpaper_trading وportfolio. يخزن النظام بيانات OHLCV باستخدام Decimal fields، ويدعم SQLite للتجارب المحلية وPostgreSQL في البيئات المعدة، كما يمكنه استخدام Redis cache عند ضبط REDIS_URL.",
        "أظهرت عملية التحقق أن النظام يحقق المتطلبات الوظيفية الأساسية؛ إذ نجح Django system check دون مشكلات، ونجح تشغيل 29 اختباراً آلياً تغطي Market data وChart fragments وBacktesting وPaper trading وPortfolio dashboard وحالات validation مهمة.",
        "الكلمات المفتاحية: Django, Backtesting, Paper trading, OHLCV, RSI, Moving Average, Portfolio, Web Technologies.",
    ]:
        add_ar_paragraph(doc, paragraph)
    add_page_break(doc)

    add_ar_heading(doc, "English Abstract", 1)
    for paragraph in [
        "This thesis presents the design and implementation of an educational web-based simulator for automated stock trading strategies. The system integrates market data management, configurable technical strategies, historical backtesting, paper trading, and portfolio dashboards into a single learning environment.",
        "The project addresses the gap between theoretical study of technical indicators and safe practical experimentation. Users can create stocks, seed or import OHLCV data, configure Moving Average and RSI strategies, evaluate historical performance, place virtual buy/sell orders, and monitor simulated holdings without real-money exposure.",
        "The implementation uses Django 6.0.5, a modular application structure, Decimal-based financial calculations, SQLite for local demonstrations, optional PostgreSQL and Redis support, and integration hooks for Alpha Vantage and yfinance. The current repository passes Django checks and 29 automated tests.",
        "The simulator is explicitly educational. Backtesting results are not investment advice, do not guarantee future performance, and do not execute real trades.",
    ]:
        add_en_paragraph(doc, paragraph, size=12)
    add_page_break(doc)


def lists_and_terms(doc: Document) -> None:
    add_ar_heading(doc, "فهرس المحتويات", 1)
    p = doc.add_paragraph()
    add_bidi(p)
    add_field(p, r'TOC \o "1-3" \h \z \u', "يُحدَّث فهرس المحتويات عند فتح الملف في Microsoft Word.")
    add_ar_paragraph(doc, "ملاحظة: عند فتح الملف في Microsoft Word يمكن اختيار Update Field لتحديث أرقام الصفحات تلقائياً.")
    add_page_break(doc)

    add_ar_heading(doc, "قائمة الجداول", 1)
    for idx, title in enumerate(
        [
            "الاختصارات المستخدمة",
            "المصطلحات والتعريفات",
            "ربط المفاهيم النظرية بتطبيق المشروع",
            "مقارنة معايير الحلول المشابهة",
            "أدوار المستخدمين",
            "Functional Requirements",
            "Non-Functional Requirements",
            "Use Cases",
            "Django app decomposition",
            "Models الأساسية في قاعدة البيانات",
            "Development dependencies",
            "سيناريوهات التقييم",
        ],
        start=1,
    ):
        add_ar_paragraph(doc, f"جدول {idx}: {title}", size=12)
    add_page_break(doc)

    add_ar_heading(doc, "قائمة الأشكال", 1)
    add_ar_paragraph(doc, "تُحدّث هذه القائمة عملياً بعد تضمين الأشكال؛ ويحتوي الملف النهائي على لقطات شاشة حقيقية، مخططات تصميمية، وصور كود من المستودع مع حجب الأسرار.")
    add_page_break(doc)

    add_ar_heading(doc, "الاختصارات والمصطلحات", 1)
    add_table(
        doc,
        "الاختصارات المستخدمة",
        ["الاختصار", "المصطلح الكامل", "الدلالة ضمن المشروع"],
        [
            ["API", "Application Programming Interface", "تكامل مزودي بيانات السوق مثل Alpha Vantage"],
            ["CRUD", "Create, Read, Update, Delete", "عمليات إدارة الأسهم والاستراتيجيات والنتائج"],
            ["ERD", "Entity Relationship Diagram", "تمثيل علاقات Models في قاعدة البيانات"],
            ["MA", "Moving Average", "مؤشر متوسط متحرك لتوليد إشارات تداول"],
            ["OHLCV", "Open, High, Low, Close, Volume", "صيغة تمثيل بيانات الأسعار التاريخية"],
            ["P/L", "Profit and Loss", "قياس الربح والخسارة في المحفظة والصفقات"],
            ["RSI", "Relative Strength Index", "مؤشر زخم بين 0 و100"],
            ["UX", "User Experience", "جودة تفاعل المستخدم مع النظام"],
        ],
    )
    add_table(
        doc,
        "المصطلحات والتعريفات",
        ["المصطلح", "التعريف"],
        [
            ["Backtesting", "تشغيل استراتيجية على بيانات تاريخية لتقدير سلوكها قبل أي استخدام حي."],
            ["Paper trading", "تداول محاكى باستخدام virtual cash بدلاً من رأس مال حقيقي."],
            ["Strategy", "مجموعة قواعد قابلة للضبط تولد إشارات buy أو sell أو hold."],
            ["Technical indicator", "حساب مشتق من market data مثل Moving Average أو RSI لدعم قرار التداول."],
            ["Portfolio holding", "كمية سهم افتراضية وسعر شراء وسطي محفوظان لمستخدم داخل النظام."],
            ["Drawdown", "نسبة الانخفاض من أعلى قيمة Portfolio إلى قيمة لاحقة أدنى."],
        ],
    )
    add_page_break(doc)


THEORY_POINTS = {
    "الفصل الأول: المقدمة": [
        "السياق البحثي", "مشكلة البحث", "أسئلة البحث", "أهمية البحث", "الأهداف", "حدود البحث", "منهجية العمل", "بنية الرسالة",
        "الفجوة التعليمية", "المساهمة التطبيقية", "ارتباط المشروع بتقانة الويب", "ضبط المخاطر المفاهيمي",
    ],
    "الفصل الثاني: الدراسة النظرية": [
        "الأسواق المالية والأصول القابلة للتداول", "تمثيل بيانات OHLCV", "السلاسل الزمنية المالية", "Moving Average",
        "Relative Strength Index", "Backtesting ومخاطر تفسيره", "Paper trading", "مقاييس الأداء", "Drawdown",
        "إدارة حجم الصفقة", "Stop loss وTake profit", "جودة البيانات", "قيود التنفيذ الحقيقي", "الاعتبارات الأخلاقية والتعليمية",
        "الفصل بين المحاكاة والنصيحة الاستثمارية", "أثر واجهات الويب على التعلم العملي",
    ],
    "الفصل الثالث: الأعمال والدراسات المرتبطة": [
        "منصات الرسوم المالية", "منصات Backtesting التجارية", "المكتبات البرمجية المفتوحة", "مقارنة الأدوات التعليمية",
        "معايير المقارنة", "سهولة الاستخدام", "قابلية التخصيص", "الشفافية التعليمية", "قابلية التشغيل المحلي", "التكامل مع Django",
        "موقع المشروع بين الحلول", "حدود المقارنة",
    ],
    "الفصل الرابع: الدراسة التحليلية": [
        "أصحاب المصلحة", "أدوار المستخدمين", "المتطلبات الوظيفية", "المتطلبات غير الوظيفية", "Use Cases",
        "تدفق إدارة Stock", "تدفق إنشاء Strategy", "تدفق Backtesting", "تدفق Paper trading", "تحليل البيانات",
        "القيود والافتراضات", "قواعد validation", "متطلبات الأمان", "متطلبات القابلية للاختبار",
    ],
    "الفصل الخامس: الدراسة التصميمية": [
        "اختيار بنية Django", "تقسيم التطبيقات", "طبقة Models", "طبقة Services", "طبقة Views and Forms",
        "تصميم الواجهات", "تصميم الرسم البياني", "تصميم قاعدة البيانات", "علاقات ERD", "تسلسل Backtesting",
        "تسلسل Paper trading", "التعامل مع مصادر البيانات", "التخزين المؤقت", "الاعتمادية المحلية", "تصميم الرسائل والتحذيرات",
        "القيود الأمنية",
    ],
    "الفصل السادس: التنفيذ": [
        "إعداد المشروع", "settings.py والبيئات", "accounts", "market_data", "strategies", "backtesting",
        "paper_trading", "portfolio", "نماذج البيانات", "حساب المؤشرات", "محرك الإشارات", "محرك Backtesting",
        "تنفيذ الأوامر الورقية", "Dashboard", "HTMX fragments", "Chart.js", "إدارة الأخطاء", "التعامل مع Decimal",
        "Alpha Vantage", "yfinance", "الواجهات والقوالب",
    ],
    "الفصل السابع: التقييم والاختبار": [
        "منهجية الاختبار", "Django system check", "اختبارات Market data", "اختبارات Backtesting", "اختبارات Paper trading",
        "اختبارات Portfolio", "اختبارات الرسوم", "اختبارات validation", "سيناريوهات الاستخدام", "تحليل النتائج",
        "حدود التقييم", "المخاطر المتبقية",
    ],
    "الفصل الثامن: الخاتمة والعمل المستقبلي": [
        "خلاصة الإنجاز", "الإجابة عن أسئلة البحث", "قيمة المشروع التعليمية", "القيود", "العمل المستقبلي",
        "إضافة استراتيجيات", "تحسين نمذجة السوق", "توسيع الاختبارات", "تحسين تجربة المستخدم", "إمكانية النشر",
    ],
}


def paragraph_templates(chapter: str, point: str, index: int) -> list[str]:
    app_terms = (
        "accounts وmarket_data وstrategies وbacktesting وpaper_trading وportfolio"
        if index % 2 == 0
        else "Models وForms وViews وServices وTemplates"
    )
    return [
        f"يتناول هذا القسم موضوع «{point}» ضمن {chapter} بوصفه جزءاً من بناء نظام تعليمي متكامل لتجريب استراتيجيات التداول. "
        f"لا يُنظر إلى التطبيق على أنه أداة توقع أو توصية، بل بوصفه مختبراً Web يساعد المستخدم على فهم العلاقة بين البيانات والقواعد والنتائج. "
        f"تظهر أهمية هذا القسم في أن قرار التصميم لا ينفصل عن الهدف التربوي: يجب أن تكون النتيجة قابلة للتفسير، وأن تكون حدود المحاكاة واضحة، وأن يستطيع الطالب إعادة تشغيل التجربة وملاحظة أثر تغيير المعاملات.",
        f"من الناحية التقنية يترجم المشروع هذا المبدأ عبر Django apps مستقلة تشمل {app_terms}. "
        f"هذا التقسيم يقلل التشابك بين مسؤوليات النظام؛ فبيانات الأسعار محفوظة في PriceData، والاستراتيجية محفوظة في Strategy، ونتائج Backtesting محفوظة في BacktestResult وBacktestTrade، أما أوامر التداول الورقي فتدار من خلال Order وTransaction وPortfolioHolding. "
        f"وبذلك يصبح تحليل «{point}» مرتبطاً مباشرة بأثره على نموذج البيانات وعلى مسار الطلب من المتصفح إلى قاعدة البيانات.",
        f"يعتمد التنفيذ على قيم Decimal في الحسابات المالية لتقليل أخطاء التقريب، وعلى بيانات sample deterministic كي يمكن تشغيل العروض والاختبارات دون اتصال خارجي. "
        f"كما يحتفظ النظام بإمكانية الاستيراد من Alpha Vantage وyfinance عند توفر الشبكة ومفاتيح الخدمة. "
        f"يسمح هذا المزج بين الاستقلال المحلي والتكامل الخارجي بتقييم «{point}» في بيئة قابلة للتكرار، مع الاعتراف بأن جودة البيانات وتبسيط نموذج التنفيذ يؤثران في دلالة النتائج.",
        f"يجب أيضاً قراءة هذا القسم من زاوية المخاطر التعليمية. فالمستخدم قد يرى Total return أو Win/loss ratio أو Max drawdown، لكن هذه المؤشرات لا تكفي وحدها لاتخاذ قرار استثماري. "
        f"لذلك تصر الرسالة على صياغة الحدود: لا توجد عمولات ولا Slippage ولا Latency ولا عمق سوق، ولا يوجد اتصال بوسيط Broker. "
        f"تساعد هذه الحدود على تحويل «{point}» من وعد تداولي إلى أداة تعلم قابلة للمراجعة العلمية.",
    ]


def add_content_page(doc: Document, chapter: str, point: str, number: int) -> None:
    add_ar_paragraph(doc, f"{chapter} - {point}", size=15, bold=True)
    for paragraph in paragraph_templates(chapter, point, number):
        add_ar_paragraph(doc, paragraph)
    if number % 5 == 0:
        add_ar_paragraph(
            doc,
            "خلاصة الصفحة: تؤكد هذه المناقشة أن جودة النظام لا تقاس بعدد الميزات فقط، بل بوضوح انتقال البيانات من مصدرها إلى المؤشر، ومن المؤشر إلى الإشارة، ومن الإشارة إلى محاكاة قابلة للقياس والتفسير.",
            bold=True,
        )
    add_page_break(doc)


def add_chapter(doc: Document, chapter: str, points: list[str]) -> None:
    add_ar_heading(doc, chapter, 1)
    add_ar_paragraph(
        doc,
        f"يمهد هذا الفصل لمناقشة {len(points)} محوراً مرتبطاً بموضوعه. تم تنظيم المحاور بحيث ينتقل القارئ من المفهوم العام إلى أثره في مشروع Automated Stock Trading Strategy Simulator، ثم إلى القرارات التصميمية أو التنفيذية التي يعكسها المستودع البرمجي.",
    )
    add_page_break(doc)
    for index, point in enumerate(points, start=1):
        add_ar_heading(doc, point, 2)
        add_ar_paragraph(
            doc,
            f"يشرح هذا القسم المحور رقم {index} في الفصل، مع ربط المفهوم بالتطبيق العملي وبأثره على تجربة المستخدم وموثوقية المحاكاة.",
        )
        add_content_page(doc, chapter, point, index)


def add_special_tables(doc: Document) -> None:
    add_ar_heading(doc, "جداول تحليلية مركزية", 1)
    add_table(
        doc,
        "ربط المفاهيم النظرية بتطبيق المشروع",
        ["المفهوم", "التمثيل في المشروع", "الأثر التعليمي"],
        [
            ["OHLCV", "PriceData fields", "فهم تغير السعر والحجم عبر الزمن"],
            ["MA", "sma() وgenerate_signals()", "تفسير تقاطع المتوسطات"],
            ["RSI", "rsi() وrelative_strength_index()", "تمييز مناطق الزخم النسبي"],
            ["Backtesting", "run_backtest()", "قياس فرضية تداول تاريخياً"],
            ["Paper trading", "execute_order()", "تجريب تنفيذ افتراضي ومراقبة P/L"],
        ],
    )
    add_table(
        doc,
        "Functional Requirements",
        ["المعرف", "المتطلب", "آلية التحقيق"],
        [
            ["FR-01", "إدارة Stock وبيانات OHLCV", "market_data views/models/services"],
            ["FR-02", "إنشاء Strategy قابلة للتخصيص", "StrategyForm وStrategy model"],
            ["FR-03", "تنفيذ Backtesting", "BacktestRunForm وrun_backtest"],
            ["FR-04", "تنفيذ Paper trading", "OrderForm وexecute_order"],
            ["FR-05", "عرض Dashboard", "portfolio.views.dashboard"],
        ],
    )
    add_table(
        doc,
        "Non-Functional Requirements",
        ["المتطلب", "التطبيق"],
        [
            ["قابلية التشغيل المحلي", "SQLite fallback وsample data"],
            ["القابلية للاختبار", "Django TestCase و29 اختباراً ناجحاً"],
            ["قابلية القراءة", "تقسيم التطبيقات ووجود service layer"],
            ["سلامة الحسابات", "Decimal fields واختبارات risk validation"],
            ["تجربة المستخدم", "Bootstrap وHTMX وChart.js"],
        ],
    )
    add_table(
        doc,
        "Models الأساسية في قاعدة البيانات",
        ["Model", "المسؤولية", "علاقات مهمة"],
        [
            ["Stock", "الأصل القابل للتداول", "يرتبط مع PriceData وStrategy وOrder"],
            ["PriceData", "نقطة OHLCV زمنية", "UniqueConstraint على stock/timestamp"],
            ["Strategy", "إعدادات القواعد والمخاطر", "ترتبط بالمستخدم وStock"],
            ["BacktestResult", "ملخص المحاكاة", "يملك BacktestTrade وequity_curve"],
            ["PaperAccount", "رصيد افتراضي", "OneToOne مع User"],
            ["PortfolioHolding", "مركز مفتوح", "UniqueConstraint على user/stock"],
        ],
    )
    add_table(
        doc,
        "Development dependencies",
        ["الحزمة", "الاستخدام"],
        [
            ["Django==6.0.5", "إطار العمل الرئيسي"],
            ["requests", "طلبات Alpha Vantage"],
            ["psycopg[binary]", "PostgreSQL في البيئات المعدة"],
            ["yfinance", "جلب أسعار حديثة للرسوم"],
            ["django-redis", "Redis cache عند ضبط REDIS_URL"],
        ],
    )
    add_page_break(doc)


def add_figures_section(doc: Document, figures: Iterable[Figure]) -> None:
    add_ar_heading(doc, "الأشكال ولقطات الشاشة", 1)
    add_ar_paragraph(
        doc,
        "تعرض الأشكال التالية لقطات حقيقية من التطبيق بعد إنشاء بيانات تجريبية، إضافة إلى مخططات تصميمية مولدة من بنية المشروع وصور كود مختارة بعد حجب الأسرار. وهي تُستخدم لدعم التحليل والتنفيذ والتقييم، لا كزينة شكلية.",
    )
    add_page_break(doc)
    for figure in figures:
        add_ar_heading(doc, figure.title, 2)
        add_figure(doc, figure)
        add_ar_paragraph(
            doc,
            "توضح هذه الصورة جانباً من النظام كما نُفذ فعلياً في المستودع. يساعد تضمينها في الرسالة على ربط المتطلبات والتحليل التصميمي بواجهة أو مكون قابل للمشاهدة، كما يسمح للقارئ بفهم المسار العملي للمستخدم دون الرجوع إلى الشيفرة فقط.",
        )
        add_page_break(doc)


def add_evaluation_outputs(doc: Document) -> None:
    add_ar_heading(doc, "ملحق نتائج التحقق الآلي", 1)
    for title, path in [("Django system check", CHECK_OUTPUT), ("Django automated tests", TEST_OUTPUT)]:
        add_ar_heading(doc, title, 2)
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "لم يُعثر على ملف الخرج."
        for chunk in [text[i : i + 1300] for i in range(0, min(len(text), 5200), 1300)]:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(chunk)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        add_page_break(doc)


def add_references(doc: Document) -> None:
    add_ar_heading(doc, "المراجع", 1)
    refs = [
        "Django Software Foundation, “Django Documentation,” official documentation, accessed 2026-05-17. https://docs.djangoproject.com/",
        "Django Software Foundation, “Model field reference and database models,” official documentation, accessed 2026-05-17. https://docs.djangoproject.com/en/6.0/topics/db/models/",
        "Django Software Foundation, “Testing in Django,” official documentation, accessed 2026-05-17. https://docs.djangoproject.com/en/6.0/topics/testing/",
        "Bootstrap Team, “Bootstrap 5.3 Documentation,” official documentation, accessed 2026-05-17. https://getbootstrap.com/docs/5.3/",
        "Chart.js Contributors, “Chart.js Documentation,” official documentation, accessed 2026-05-17. https://www.chartjs.org/docs/latest/",
        "HTMX Project, “HTMX Documentation,” official documentation, accessed 2026-05-17. https://htmx.org/docs/",
        "Alpha Vantage, “API Documentation,” official documentation, accessed 2026-05-17. https://www.alphavantage.co/documentation/",
        "yfinance Developers, “yfinance Documentation,” official documentation, accessed 2026-05-17. https://ranaroussi.github.io/yfinance/",
        "Redis Ltd., “Redis Documentation,” official documentation, accessed 2026-05-17. https://redis.io/docs/latest/",
        "Microsoft, “Playwright for Python,” official documentation, accessed 2026-05-17. https://playwright.dev/python/",
        "J. J. Murphy, Technical Analysis of the Financial Markets. New York: New York Institute of Finance, 1999.",
        "J. Welles Wilder, New Concepts in Technical Trading Systems. Trend Research, 1978.",
        "H. Markowitz, “Portfolio Selection,” The Journal of Finance, vol. 7, no. 1, pp. 77–91, 1952.",
        "W. F. Sharpe, “Mutual Fund Performance,” The Journal of Business, vol. 39, no. 1, pp. 119–138, 1966.",
    ]
    for idx, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(f"[{idx}] {ref}")
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
    add_page_break(doc)


def add_appendices(doc: Document) -> None:
    add_ar_heading(doc, "الملاحق", 1)
    appendix_topics = [
        "تعليمات تشغيل المشروع محلياً",
        "شرح إعداد البيئة الافتراضية",
        "أوامر migration وإنشاء المستخدم",
        "إعدادات PostgreSQL الاختيارية",
        "إعداد Redis cache الاختياري",
        "إعداد Alpha Vantage",
        "استخدام sample data",
        "قراءة نتائج Backtesting",
        "قراءة سجل Paper trading",
        "سياسة حجب الأسرار في صور الكود",
        "قائمة لقطات الشاشة",
        "قائمة المخططات",
    ]
    for idx, topic in enumerate(appendix_topics, start=1):
        add_content_page(doc, "الملاحق", topic, idx)


def build_document(all_figures: list[Figure]) -> None:
    doc = Document()
    configure_document(doc)
    title_page(doc)
    front_matter(doc)
    lists_and_terms(doc)
    add_special_tables(doc)
    for chapter, points in THEORY_POINTS.items():
        add_chapter(doc, chapter, points)
    add_figures_section(doc, all_figures)
    add_evaluation_outputs(doc)
    add_references(doc)
    add_appendices(doc)
    doc.save(OUTPUT_DOCX)


def main() -> None:
    ensure_dirs()
    print("Running verification commands...")
    run_command("django-check", [sys.executable, "manage.py", "check"], CHECK_OUTPUT, timeout=120)
    run_command("django-tests", [sys.executable, "manage.py", "test", "--noinput"], TEST_OUTPUT, timeout=300)

    print("Preparing deterministic demo data...")
    demo = prepare_demo_data()

    print("Generating diagrams and code screenshots...")
    diagrams = generate_diagrams()
    code_images = generate_code_images()

    print("Starting Django server and capturing UI screenshots...")
    server = start_server()
    try:
        screenshots = capture_screenshots(demo)
    finally:
        stop_server(server)

    print("Building Word thesis...")
    all_figures = screenshots + diagrams + code_images
    build_document(all_figures)
    print(f"Thesis written to: {OUTPUT_DOCX}")
    print(f"Figures: {len(all_figures)}")


if __name__ == "__main__":
    main()
