from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_db
from app.crud.stock import get_all_stocks_with_data, calculate_stock_changes
from models import Stock
from shared.schemas.stock import StockResponse, StockCreateRequest
from utils.data_update import create_stock

router = APIRouter()


@router.get("/", response_model=list[StockResponse])
def read_stocks(db: Session = Depends(get_db)):
    """Retrieve all stocks with current price and performance changes."""
    return get_all_stocks_with_data(db)


@router.get("/{ticker}", response_model=StockResponse)
def read_stock(ticker: str, db: Session = Depends(get_db)):
    """Retrieve a single stock by ticker."""
    stock = db.exec(select(Stock).where(Stock.ticker == ticker.upper())).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    price_current, changes = calculate_stock_changes(db, stock)
    return StockResponse(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        yf_ticker=stock.yf_ticker,
        price=price_current,
        change=changes,
    )


@router.post("/", response_model=StockResponse, status_code=201)
def add_stock(stock_in: StockCreateRequest, db: Session = Depends(get_db)):
    """Add a new stock to the database."""
    existing = db.exec(select(Stock).where(Stock.ticker == stock_in.ticker.upper())).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stock {stock_in.ticker} already exists")

    stock = create_stock(
        ticker=stock_in.ticker.upper(),
        name=stock_in.name,
        yf_ticker=stock_in.yf_ticker,
    )

    return StockResponse(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        yf_ticker=stock.yf_ticker,
    )
