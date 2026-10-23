import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, desc, select

from app.core.database import get_db
from app.crud.stock import calculate_stock_changes, get_all_stocks, get_stock_by_symbol
from app.services.stock_sync import sync_all_active_stocks, sync_stock_data
from models import Stock, StockDividend, StockPrice
from shared.schemas import (
    StockCreateRequest,
    StockDividendResponse,
    StockPriceResponse,
    StockResponse,
    StockSyncSummary,
)

router = APIRouter()


@router.get("/", response_model=list[StockResponse])
def read_stocks(db: Session = Depends(get_db)):
    """Retrieve all stocks with latest cached price and performance changes."""
    return get_all_stocks(db)


@router.post("/sync", response_model=StockSyncSummary)
def sync_stocks(
    yf_ticker: str | None = Query(default=None, description="Optional yf_ticker to sync a single stock"),
    db: Session = Depends(get_db),
):
    """Sync daily stock OHLCV prices and dividends incrementally.

    If yf_ticker is provided, syncs only that stock.
    Otherwise, checks and syncs all active stocks in the database.
    """
    if yf_ticker:
        stock = get_stock_by_symbol(db, yf_ticker)
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {yf_ticker} not found")

        result = sync_stock_data(db, stock)
        return StockSyncSummary(
            message=f"Sync completed for {stock.yf_ticker}: {result.status}",
            total_checked=1,
            updated_count=1 if result.status == "updated" else 0,
            skipped_count=1 if result.status == "skipped" else 0,
            error_count=1 if result.status == "error" else 0,
            results=[result],
        )

    return sync_all_active_stocks(db)


@router.get("/{yf_ticker}", response_model=StockResponse)
def read_stock(yf_ticker: str, db: Session = Depends(get_db)):
    """Retrieve a single stock by yf_ticker (or local ticker)."""
    stock = get_stock_by_symbol(db, yf_ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {yf_ticker} not found")

    assert stock.id is not None
    price_current, changes = calculate_stock_changes(db, stock)
    return StockResponse(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        yf_ticker=stock.yf_ticker,
        country=getattr(stock, "country", "USA"),
        exchange=getattr(stock, "exchange", None),
        currency=getattr(stock, "currency", "USD"),
        sector=getattr(stock, "sector", None),
        industry=getattr(stock, "industry", None),
        is_active=getattr(stock, "is_active", True),
        created_at=getattr(stock, "created_at", None),
        latest_price=getattr(stock, "latest_price", None),
        latest_price_update_at=getattr(stock, "latest_price_update_at", None),
        change=changes,
    )


@router.get("/{yf_ticker}/prices", response_model=list[StockPriceResponse])
def read_stock_prices(
    yf_ticker: str,
    start_date: datetime.date | None = Query(default=None, description="Start date (inclusive)"),
    end_date: datetime.date | None = Query(default=None, description="End date (inclusive)"),
    db: Session = Depends(get_db),
):
    """Retrieve daily historical prices for a stock."""
    stock = get_stock_by_symbol(db, yf_ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {yf_ticker} not found")

    assert stock.id is not None
    query = select(StockPrice).where(StockPrice.stock_id == stock.id)
    if start_date:
        query = query.where(StockPrice.date >= start_date)
    if end_date:
        query = query.where(StockPrice.date <= end_date)
    query = query.order_by(desc(StockPrice.date))

    return list(db.exec(query).all())


@router.get("/{yf_ticker}/dividends", response_model=list[StockDividendResponse])
def read_stock_dividends(yf_ticker: str, db: Session = Depends(get_db)):
    """Retrieve dividend distribution events for a stock."""
    stock = get_stock_by_symbol(db, yf_ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {yf_ticker} not found")

    assert stock.id is not None
    query = (
        select(StockDividend)
        .where(StockDividend.stock_id == stock.id)
        .order_by(desc(StockDividend.ex_date))
    )
    return list(db.exec(query).all())


@router.post("/", response_model=StockResponse, status_code=201)
def add_stock(stock_in: StockCreateRequest, db: Session = Depends(get_db)):
    """Add a new stock to the database and backfill 1 year of daily historical data."""
    clean_ticker = stock_in.ticker.strip().upper()
    clean_yf_ticker = stock_in.yf_ticker.strip().upper()
    clean_country = stock_in.country.strip().upper()

    # Prevent duplicate yf_ticker
    existing_yf = db.exec(select(Stock).where(Stock.yf_ticker == clean_yf_ticker)).first()
    if existing_yf:
        raise HTTPException(status_code=400, detail=f"Stock with Yahoo Finance ticker '{clean_yf_ticker}' already exists")

    # Prevent duplicate (ticker, country)
    existing_ticker = db.exec(
        select(Stock).where(Stock.ticker == clean_ticker, Stock.country == clean_country)
    ).first()
    if existing_ticker:
        raise HTTPException(
            status_code=400,
            detail=f"Stock with ticker '{clean_ticker}' already exists in country '{clean_country}'",
        )

    stock = Stock(
        ticker=clean_ticker,
        name=stock_in.name.strip(),
        yf_ticker=clean_yf_ticker,
        country=clean_country,
        exchange=stock_in.exchange.strip().upper() if stock_in.exchange else None,
        currency=stock_in.currency.strip().upper(),
        sector=stock_in.sector,
        industry=stock_in.industry,
        is_active=stock_in.is_active,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)

    # Automatically backfill 1 year of historical OHLCV prices and dividends
    sync_stock_data(db, stock, force_full_year=True)
    db.refresh(stock)

    assert stock.id is not None
    price_current, changes = calculate_stock_changes(db, stock)

    return StockResponse(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        yf_ticker=stock.yf_ticker,
        country=stock.country,
        exchange=stock.exchange,
        currency=stock.currency,
        sector=stock.sector,
        industry=stock.industry,
        is_active=stock.is_active,
        created_at=stock.created_at,
        latest_price=stock.latest_price,
        latest_price_update_at=stock.latest_price_update_at,
        change=changes,
    )
