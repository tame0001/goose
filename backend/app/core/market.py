import datetime
from zoneinfo import ZoneInfo


class MarketSchedule:
    def __init__(
        self,
        timezone_str: str,
        open_time: datetime.time,
        close_time: datetime.time,
    ):
        self.timezone: ZoneInfo = ZoneInfo(timezone_str)
        self.open_time: datetime.time = open_time
        self.close_time: datetime.time = close_time


# Hardcoded schedules for Thai (SET) and US (NYSE/NASDAQ) markets
# SET: 10:00 - 16:30 ICT (ignoring lunch break per requirements)
# US:  09:30 - 16:00 EDT/EST
MARKET_SCHEDULES: dict[str, MarketSchedule] = {
    # Thailand (SET)
    "THAILAND": MarketSchedule("Asia/Bangkok", datetime.time(10, 0), datetime.time(16, 30)),
    "SET": MarketSchedule("Asia/Bangkok", datetime.time(10, 0), datetime.time(16, 30)),

    # United States (NYSE, NASDAQ)
    "USA": MarketSchedule("America/New_York", datetime.time(9, 30), datetime.time(16, 0)),
    "US": MarketSchedule("America/New_York", datetime.time(9, 30), datetime.time(16, 0)),
    "NYSE": MarketSchedule("America/New_York", datetime.time(9, 30), datetime.time(16, 0)),
    "NASDAQ": MarketSchedule("America/New_York", datetime.time(9, 30), datetime.time(16, 0)),
}

DEFAULT_SCHEDULE = MARKET_SCHEDULES["USA"]


def get_schedule(country: str, exchange: str | None = None) -> MarketSchedule:
    """Resolve the market schedule for a given country or exchange."""
    if exchange and exchange.strip().upper() in MARKET_SCHEDULES:
        return MARKET_SCHEDULES[exchange.strip().upper()]
    return MARKET_SCHEDULES.get(country.strip().upper(), DEFAULT_SCHEDULE)


def get_market_local_now(country: str, exchange: str | None = None) -> datetime.datetime:
    """Return the current local datetime in the market's timezone."""
    schedule = get_schedule(country, exchange)
    return datetime.datetime.now(datetime.timezone.utc).astimezone(schedule.timezone)


def is_market_open(country: str, exchange: str | None = None) -> bool:
    """Check if the market is currently in an active trading session.

    Returns True if:
      - Day is Monday to Friday (weekday 0-4)
      - Market local time is between opening and closing bell
    """
    local_now = get_market_local_now(country, exchange)
    if local_now.weekday() >= 5:
        return False
    schedule = get_schedule(country, exchange)
    return schedule.open_time <= local_now.time() <= schedule.close_time


def is_session_settled(country: str, exchange: str | None = None, date_to_check: datetime.date | None = None) -> bool:
    """Check if the trading session for a given date is fully closed and settled.

    If date_to_check is before today's market date, it is already settled.
    If date_to_check is today, it is only settled if local time is past closing bell.
    Future dates are not settled.
    """
    local_now = get_market_local_now(country, exchange)
    local_today = local_now.date()
    target_date = date_to_check or local_today

    if target_date < local_today:
        return True
    if target_date > local_today:
        return False

    # For today: weekend is closed/settled from Friday, weekday is settled only after close
    if local_now.weekday() >= 5:
        return False
    schedule = get_schedule(country, exchange)
    return local_now.time() >= schedule.close_time
