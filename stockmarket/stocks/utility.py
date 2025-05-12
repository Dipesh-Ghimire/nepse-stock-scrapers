from datetime import datetime
from stocks.models import CompanyProfile, PriceHistory, FloorSheet, CompanyNews
from django.utils import timezone
from dateutil.parser import parse as parse_datetime
import logging

logger = logging.getLogger("stocks")

def save_price_history_to_db(symbol, price_history_data):
    """
    Save standardized price history data to the Django DB.
    Supports NepalStock format
    """
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        logger.warning(f"🚫 Company '{symbol}' not found in DB.")
        return

    for record in price_history_data:
        try:
            date_str = record.get("Date")
            if not date_str:
                continue

            # Format date (handles both YYYY-MM-DD and DD/MM/YYYY etc.)
            date_obj = try_parse_date(date_str)
            if not date_obj:
                logger.warning(f"⚠️ Could not parse date: {date_str}")
                continue

            # Avoid duplicates
            if PriceHistory.objects.filter(company=company, date=date_obj).exists():
                logger.info(f"🟡 Already exists: {symbol} - {date_str}")
                continue

            # Normalize keys from different scrapers
            open_price = record.get("Open") or record.get("Open Price")
            high_price = record.get("High")
            low_price = record.get("Low")
            close_price = record.get("Close") or record.get("LTP")

            price_entry = PriceHistory(
                company=company,
                date=date_obj,
                open_price=safe_float(open_price),
                high_price=safe_float(high_price),
                low_price=safe_float(low_price),
                close_price=safe_float(close_price)
            )
            price_entry.save()
            # logger.info(f" Saved: {symbol} - {date_obj}")

        except Exception as e:
            logger.error(f" Error saving record: {record}, Error: {e}")

def try_parse_date(date_str):
    """
    Try parsing date string using multiple known formats.
    """
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def save_price_history_to_db_ml(symbol, price_history_data):
    """
    Save Merolagani price history data to the Django DB.
    """
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        logger.error(f" Company with symbol '{symbol}' not found.")
        return

    for record in price_history_data:
        try:
            date_str = record["Date"].replace("/", "-")  # Convert format to YYYY-MM-DD
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            if PriceHistory.objects.filter(company=company, date=date_obj).exists():
                logger.info(f"⚠ Skipping existing record: {symbol} - {date_str}")
                continue

            # Safely convert fields
            open_price = float(record["Open"].replace(",", ""))
            high_price = float(record["High"].replace(",", ""))
            low_price = float(record["Low"].replace(",", ""))
            close_price = float(record["LTP"].replace(",", ""))

            # Save record
            price_entry = PriceHistory(
                company=company,
                date=date_obj,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
            )
            price_entry.save()
            # logger.info(f" Saved: {symbol} - {date_str}")
        except Exception as e:
            logger.error(f" Failed to save record: {record}")

def save_price_history_to_db_ss(symbol, price_history_data):
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        logger.error(f"Company with symbol '{symbol}' not found.")
        return

    for record in price_history_data:
        try:
            date_obj = datetime.strptime(record["Date"], "%Y-%m-%d").date()

            if PriceHistory.objects.filter(company=company, date=date_obj).exists():
                logger.info(f"⚠ Skipping existing record: {symbol} - {record['Date']}")
                continue

            price_entry = PriceHistory(
                company=company,
                date=date_obj,
                open_price=float(record["Open"].replace(",", "")),
                high_price=float(record["High"].replace(",", "")),
                low_price=float(record["Low"].replace(",", "")),
                close_price=float(record["Close"].replace(",", ""))
            )
            price_entry.save()
            # logger.info(f" Saved: {symbol} - {record['Date']}")
        except Exception as e:
            logger.error(f" Failed to save record: {record}")

def store_floorsheet_to_db_ss(symbol, floorsheet_data):
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        logger.error(f"Company with symbol '{symbol}' not found.")
        return

    for record in floorsheet_data:
        try:
            transaction_id = record["transaction_id"]
            if FloorSheet.objects.filter(company=company, transaction_id=transaction_id).exists():
                logger.info(f"⚠ Skipping existing record: {symbol} - {record['date']}")
                continue

            floorsheet_entry = FloorSheet(
                company=company,
                date=record["date"],
                transaction_id=transaction_id,
                buyer=record["buyer"],
                seller=record["seller"],
                quantity=record["quantity"],
                rate=record["rate"],
                amount=record["amount"]
            )
            floorsheet_entry.save()
        except Exception as e:
            logger.error(f"Failed to save record: {transaction_id}")
    
    logger.info(f" Saved Floorsheet to DB: {symbol}")
    
def store_floorsheet_to_db_ml(symbol, floorsheet_data):
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        logger.error(f"Company with symbol '{symbol}' not found in database.")
        return

    for record in floorsheet_data:
        try:
            transaction_id = record["Transact. No."]
            if FloorSheet.objects.filter(company=company, transaction_id=transaction_id).exists():
                logger.info(f"⚠ Skipping existing record: {symbol} - {transaction_id}")
                continue

            floorsheet_entry = FloorSheet(
                company=company,
                date=try_parse_date(record["Date"]),
                transaction_id=transaction_id,
                buyer=record["Buyer"],
                seller=record["Seller"],
                quantity=record["Quantity"].replace(",", ""),
                rate=record["Rate"].replace(",", ""),
                amount=record["Amount"].replace(",", "")
            )
            floorsheet_entry.save()
        except Exception as e:
            logger.error(f"Failed to save record: {transaction_id} | Error: {e}")

    logger.info(f"Saved Floorsheet data to DB for symbol: {symbol}")

def safe_float(value):
    try:
        return float(value.replace(',', '').strip()) if value else None
    except Exception:
        return None

def get_latest_data_of_pricehistory(symbol):
    """
    Get the latest data of price history for a given symbol.
    """
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
        latest_entry = PriceHistory.objects.filter(company=company).order_by('-date').first()
        if latest_entry:
            return latest_entry.date
        else:
            logger.warning(f"No price history found for {symbol}.")
            return None
    except CompanyProfile.DoesNotExist:
        logger.error(f"Company with symbol '{symbol}' not found.")
        return None

def store_news_to_db_ml(news_data):
    for record in news_data:
        try:
            # Skip if URL already exists
            if CompanyNews.objects.filter(news_url=record["url"]).exists():
                logger.info(f"⚠ Skipping existing news: {record['url']}")
                continue
            news_entry = CompanyNews(
                company=None,
                news_url=record["url"],
                news_title=record["title"],
                news_date=record["date"],
                news_image=record.get("image"),
                news_body=record.get("body", "")
            )
            news_entry.save()
            logger.info(f"Saved news: {record['title']}")

        except Exception as e:
            logger.error(f"Failed to save news: {record["title"]} | Error: {e}")

def get_latest_news_date():
    latest_news = CompanyNews.objects.order_by('-news_date').first()
    return latest_news.news_date if latest_news else None