import datetime
from decimal import Decimal
import logging
import pandas as pd
from sqlmodel import Session, select
import yfinance as yf

from app.core.market import get_market_local_now, get_schedule, is_session_settled
from app.crud.stock import get_latest_price_date
from models import Stock, StockDividend, StockPrice
from shared.schemas.sync import StockSyncResult, StockSyncSummary

logger = logging.getLogger(__name__)


def _is_up_to_date(stock: Stock, latest_date: datetime.date | None) -> tuple[bool, str]:
    """Check if the stock's settled daily history is up to date based on market hours."""
    if latest_date is None:
        return False, "No historical data in database"

    local_now = get_market_local_now(stock.country, stock.exchange)
    local_today = local_now.date()
    schedule = get_schedule(stock.country, stock.exchange)

    # 1. Weekend check: if today is Saturday (5) or Sunday (6), latest settled day is Friday
    if local_now.weekday() >= 5:
        last_friday = local_today - datetime.timedelta(days=local_now.weekday() - 4)
        if latest_date >= last_friday:
            return True, "Market closed on weekend; latest session already recorded"
        return False, "Needs update for previous week"

    # 2. Weekday before closing bell: latest settled day is previous trading session
    if local_now.time() < schedule.close_time:
        days_back = 3 if local_now.weekday() == 0 else 1  # If Monday, previous is Friday
        prev_session = local_today - datetime.timedelta(days=days_back)
        if latest_date >= prev_session:
            return True, "Latest settled session recorded; current session not closed yet"
        return False, "Needs update for previous sessions"

    # 3. Weekday after closing bell: today's session is now settled
    if latest_date >= local_today:
        return True, "Already up to date with today's closing price"

    return False, "Needs today's closing price"


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
    """Process history DataFrame: update Stock.latest_price and save settled daily bars."""
    assert stock.id is not None
    if history.empty:
        return 0, 0

    valid_df = history.dropna(subset=["Close"])
    if valid_df.empty:
        return 0, 0

    # 1. Update Stock entity with the very latest quote & update timestamp
    latest_val = Decimal(f"{valid_df['Close'].iloc[-1]:.2f}")
    stock.latest_price = latest_val
    stock.latest_price_update_at = datetime.datetime.now(datetime.timezone.utc)
    session.add(stock)

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
    seen_dates: set[datetime.date] = set()

    # 3. Insert only settled trading days into StockPrice
    for p_date, p_open, p_high, p_low, p_close, p_adj, p_vol, p_div in zip(
        dates, opens, highs, lows, closes, adj_closes, volumes, dividends
    ):
        # Do not record OHLCV if the trading session is still open / unsettled
        if not is_session_settled(stock.country, stock.exchange, p_date):
            logger.debug(f"Skipping unsettled intraday bar {p_date} for {stock.yf_ticker}")
            continue

        if p_date in seen_dates:
            continue
        seen_dates.add(p_date)

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
    local_now = get_market_local_now(stock.country, stock.exchange)
    today = local_now.date()
    latest_date = get_latest_price_date(session, stock.id)

    if not force_full_year:
        up_to_date, reason = _is_up_to_date(stock, latest_date)
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
    has_updates = new_prices > 0 or new_divs > 0 or (stock.latest_price is not None)

    return StockSyncResult(
        yf_ticker=stock.yf_ticker,
        status="updated" if has_updates else "skipped",
        new_price_records=new_prices,
        new_dividend_records=new_divs,
        latest_date=updated_date,
        reason=f"Added {new_prices} prices, {new_divs} dividends, quote {stock.latest_price}" if has_updates else "No new market sessions",
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
        up_to_date, reason = _is_up_to_date(stock, latest_date)

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
            local_now = get_market_local_now(stock.country, stock.exchange)
            local_today = local_now.date()
            start_date = (local_today - datetime.timedelta(days=365)) if latest_date is None else (latest_date + datetime.timedelta(days=1))
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

        # Step 3: Vectorized extraction per ticker
        for stock in stock_batch:
            assert stock.id is not None
            ticker_df = _extract_ticker_df(batch_df, stock.yf_ticker)
            new_prices, new_divs = _save_ticker_history(session, stock, ticker_df)
            has_updates = new_prices > 0 or new_divs > 0 or (stock.latest_price is not None)

            if has_updates:
                updated_count += 1
            else:
                skipped_count += 1

            results.append(
                StockSyncResult(
                    yf_ticker=stock.yf_ticker,
                    status="updated" if has_updates else "skipped",
                    new_price_records=new_prices,
                    new_dividend_records=new_divs,
                    latest_date=get_latest_price_date(session, stock.id),
                    reason=f"Batch processed: added {new_prices} prices, {new_divs} dividends, quote {stock.latest_price}",
                )
            )

        session.commit()

    summary_msg = f"Incremental sync completed: {updated_count} updated, {skipped_count} skipped, {error_count} errors"
    return StockSyncSummary(
        message=summary_msg,
        total_checked=len(stocks),
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        results=results,
    )
