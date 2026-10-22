import datetime
from decimal import Decimal
import logging
import pandas as pd
from sqlmodel import Session, select
import yfinance as yf

from app.crud.stock import get_latest_price_date
from models import Stock, StockDividend, StockPrice
from shared.schemas.sync import StockSyncResult, StockSyncSummary

logger = logging.getLogger(__name__)


def _is_up_to_date(latest_date: datetime.date | None, today: datetime.date) -> tuple[bool, str]:
    """Check if the stock data is already up to date without making any network calls."""
    if latest_date is None:
        return False, "No historical data in database"

    if latest_date >= today:
        return True, "Already up to date"

    # Weekend check: If today is Saturday (5) or Sunday (6) and we have Friday's data
    if today.weekday() >= 5:
        last_friday = today - datetime.timedelta(days=today.weekday() - 4)
        if latest_date >= last_friday:
            return True, "Market closed on weekend; latest session already recorded"

    # If tomorrow's start date would be beyond today
    if latest_date + datetime.timedelta(days=1) > today:
        return True, "Already up to date"

    return False, "Needs update"


def _extract_ticker_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract a single ticker's DataFrame from a multi-ticker yf.download result."""
    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        # When grouped by ticker (level 0 is ticker)
        if ticker in df.columns.levels[0]:
            sub_df = df[ticker]
            if isinstance(sub_df, pd.DataFrame):
                return sub_df
            if isinstance(sub_df, pd.Series):
                return sub_df.to_frame()
        # When grouped by column (level 1 is ticker)
        if len(df.columns.levels) > 1 and ticker in df.columns.levels[1]:
            sub_df = df.xs(ticker, axis=1, level=1)
            if isinstance(sub_df, pd.DataFrame):
                return sub_df
            if isinstance(sub_df, pd.Series):
                return sub_df.to_frame()
    return df


def _save_ticker_history(
    session: Session,
    stock: Stock,
    history: pd.DataFrame,
) -> tuple[int, int]:
    """Vectorize history DataFrame and insert new StockPrice and StockDividend rows directly into SQLite."""
    assert stock.id is not None
    if history.empty:
        return 0, 0

    # 1. Vectorized filter in C: drop rows where market was closed for this ticker
    valid_df = history.dropna(subset=["Close"])
    if valid_df.empty:
        return 0, 0

    # 2. Extract strongly-typed column vectors
    adj_series = valid_df["Adj Close"] if "Adj Close" in valid_df else valid_df["Close"]
    div_series = valid_df["Dividends"] if "Dividends" in valid_df else pd.Series(0.0, index=valid_df.index)

    dates = [ts.date() for ts in valid_df.index]
    opens = [Decimal(f"{v:.2f}") for v in valid_df["Open"]]
    highs = [Decimal(f"{v:.2f}") for v in valid_df["High"]]
    lows = [Decimal(f"{v:.2f}") for v in valid_df["Low"]]
    closes = [Decimal(f"{v:.2f}") for v in valid_df["Close"]]
    adj_closes = [Decimal(f"{v:.2f}") for v in adj_series]
    volumes = valid_df["Volume"].astype(int).tolist()
    dividends = [Decimal(f"{v:.2f}") for v in div_series]

    new_prices = 0
    new_dividends = 0

    # 3. Direct creation of database models from zipped vectors
    for p_date, p_open, p_high, p_low, p_close, p_adj, p_vol, p_div in zip(
        dates, opens, highs, lows, closes, adj_closes, volumes, dividends
    ):
        price_record = StockPrice(
            stock_id=stock.id,
            date=p_date,
            open=p_open,
            high=p_high,
            low=p_low,
            close=p_close,
            adj_close=p_adj,
            volume=p_vol,
        )
        session.add(price_record)
        new_prices += 1

        # Record cash dividend payouts
        if p_div > Decimal("0.0"):
            div_record = StockDividend(
                stock_id=stock.id,
                ex_date=p_date,
                amount=p_div,
                currency=stock.currency,
            )
            session.add(div_record)
            new_dividends += 1

    return new_prices, new_dividends


def sync_stock_data(
    session: Session,
    stock: Stock,
    force_full_year: bool = False,
) -> StockSyncResult:
    """Sync a single stock individually (used when adding a stock or requesting single sync)."""
    assert stock.id is not None
    today = datetime.date.today()
    latest_date = get_latest_price_date(session, stock.id)

    if not force_full_year:
        up_to_date, reason = _is_up_to_date(latest_date, today)
        if up_to_date:
            return StockSyncResult(
                yf_ticker=stock.yf_ticker,
                status="skipped",
                latest_date=latest_date,
                reason=reason,
            )

    start_date = (today - datetime.timedelta(days=365)) if (force_full_year or latest_date is None) else (latest_date + datetime.timedelta(days=1))
    end_date = today + datetime.timedelta(days=1)

    try:
        yf_stock = yf.Ticker(stock.yf_ticker)
        history = yf_stock.history(start=start_date, end=end_date, auto_adjust=False)
    except Exception as exc:
        logger.error(f"yfinance error for {stock.yf_ticker}: {exc}")
        return StockSyncResult(
            yf_ticker=stock.yf_ticker,
            status="error",
            latest_date=latest_date,
            reason=f"yfinance error: {str(exc)}",
        )

    new_prices, new_divs = _save_ticker_history(session, stock, history)
    session.commit()

    updated_date = get_latest_price_date(session, stock.id)
    has_updates = new_prices > 0 or new_divs > 0

    return StockSyncResult(
        yf_ticker=stock.yf_ticker,
        status="updated" if has_updates else "skipped",
        new_price_records=new_prices,
        new_dividend_records=new_divs,
        latest_date=updated_date,
        reason=f"Added {new_prices} prices, {new_divs} dividends" if has_updates else "No new market sessions",
    )


def sync_all_active_stocks(session: Session) -> StockSyncSummary:
    """Routine bulk sync for all active stocks using group-by-date batching.

    Minimizes network calls by:
    1. Skipping all stocks that are already up-to-date (0 network calls).
    2. Grouping remaining stocks by start_date (e.g. US batch vs Thai batch).
    3. Downloading all tickers in each group in a single yf.download() call.
    """
    stocks = session.exec(select(Stock).where(Stock.is_active == True)).all()  # noqa: E712
    today = datetime.date.today()

    results: list[StockSyncResult] = []
    # Map start_date -> list of Stock objects
    batches_by_date: dict[datetime.date, list[Stock]] = {}

    updated_count = 0
    skipped_count = 0
    error_count = 0

    # Step 1: Local inspection (zero network calls)
    for stock in stocks:
        assert stock.id is not None
        latest_date = get_latest_price_date(session, stock.id)
        up_to_date, reason = _is_up_to_date(latest_date, today)

        if up_to_date:
            results.append(
                StockSyncResult(
                    yf_ticker=stock.yf_ticker,
                    status="skipped",
                    latest_date=latest_date,
                    reason=reason,
                )
            )
            skipped_count += 1
        else:
            start_date = (today - datetime.timedelta(days=365)) if latest_date is None else (latest_date + datetime.timedelta(days=1))
            batches_by_date.setdefault(start_date, []).append(stock)

    # Step 2: Download each batch in a single call
    end_date = today + datetime.timedelta(days=1)

    for start_date, stock_batch in batches_by_date.items():
        tickers = [s.yf_ticker for s in stock_batch]

        # Single stock fallback
        if len(tickers) == 1:
            res = sync_stock_data(session, stock_batch[0])
            results.append(res)
            if res.status == "updated":
                updated_count += 1
            elif res.status == "skipped":
                skipped_count += 1
            else:
                error_count += 1
            continue

        # Multi-ticker batch download
        try:
            logger.info(f"Batch downloading {len(tickers)} tickers from {start_date} to {end_date}...")
            batch_df = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                actions=True,        # Includes Dividends
                auto_adjust=False,   # Includes raw Close + Adj Close
                group_by="ticker",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            logger.error(f"Batch download failed for {tickers}: {exc}")
            for stock in stock_batch:
                results.append(
                    StockSyncResult(
                        yf_ticker=stock.yf_ticker,
                        status="error",
                        reason=f"Batch download error: {str(exc)}",
                    )
                )
                error_count += 1
            continue

        # Step 3: Parse and save each stock in this batch
        assert batch_df is not None
        for stock in stock_batch:
            ticker_df = _extract_ticker_df(batch_df, stock.yf_ticker)
            new_prices, new_divs = _save_ticker_history(session, stock, ticker_df)
            has_updates = new_prices > 0 or new_divs > 0
            assert stock.id is not None
            updated_latest_date = get_latest_price_date(session, stock.id)

            status = "updated" if has_updates else "skipped"
            if has_updates:
                updated_count += 1
            else:
                skipped_count += 1

            results.append(
                StockSyncResult(
                    yf_ticker=stock.yf_ticker,
                    status=status,
                    new_price_records=new_prices,
                    new_dividend_records=new_divs,
                    latest_date=updated_latest_date,
                    reason=f"Added {new_prices} prices, {new_divs} dividends" if has_updates else "No new market sessions",
                )
            )

    # Commit all batch changes at once
    session.commit()

    return StockSyncSummary(
        message=f"Sync finished: {updated_count} updated, {skipped_count} skipped, {error_count} errors across {len(batches_by_date)} batch calls",
        total_checked=len(stocks),
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        results=results,
    )
