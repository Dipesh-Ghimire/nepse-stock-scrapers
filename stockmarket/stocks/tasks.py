from celery import shared_task
from .utility import save_price_history_to_db, save_price_history_to_db_ss, save_price_history_to_db_ml, store_floorsheet_to_db_ss, store_floorsheet_to_db_ml, store_news_to_db_ml
from .scrapers.sharesansar_scraper import SharesansarPriceScraper, SharesansarFloorsheetScraper
from .scrapers.merolagani_scraper import MerolaganiScraper, MerolaganiFloorsheetScraper, MerolaganiNewsScraper
from .scrapers.nepstock_scraper import scrape_company_price_history_nepstock, scrape_company_floorsheet_nepstock
from .models import CompanyProfile

import logging
logger = logging.getLogger('stocks')

@shared_task(bind=True)
def run_sharesansar_pricehistory_scraper(self):
    logger.info("Celery Task Started: Sharesansar Price History Scraper")
    symbols = CompanyProfile.objects.values_list('symbol', flat=True)
    for symbol in symbols:
        logger.info(f"Celery: Processing for {symbol}")
        scraper = SharesansarPriceScraper(symbol=symbol, headless=True)
        data = scraper.fetch_price_history()
        logger.info(f"Celery: Data Scraped for {symbol}")
        save_price_history_to_db_ss(symbol, data)
        logger.info(f"Celery: Data saved for {symbol}")
    return "Celery Task Executed"

@shared_task(bind=True)
def run_merolagani_pricehistory_scraper(self):
    logger.info("Celery Task Started: Merolagani Price History Scraper")
    symbols = CompanyProfile.objects.values_list('symbol', flat=True)
    for symbol in symbols:
        logger.info(f"Celery: Processing for {symbol}")
        scraper = MerolaganiScraper(symbol=symbol, headless=True)
        data = scraper.fetch_price_history(max_records=80)
        logger.info(f"Celery: Data Scraped for {symbol}")
        save_price_history_to_db_ml(symbol, data)
        logger.info(f"Celery: Data saved for {symbol}")
    return "Celery Task Executed"

@shared_task(bind=True)
def run_nepstock_pricehistory_scraper(self):
    logger.info("Celery Task Started: Nepstock Price History Scraper")
    symbols = CompanyProfile.objects.values_list('symbol', flat=True)
    for symbol in symbols:
        logger.info(f"Celery: Processing for {symbol}")
        price_history_data = scrape_company_price_history_nepstock(symbol, max_pages=8, output_csv=False)
        logger.info(f"Celery: Data Scraped for {symbol}")
        save_price_history_to_db(symbol, price_history_data)
        logger.info(f"Celery: Data saved for {symbol}")
    return "Celery Task Executed"

@shared_task(bind=True)
def run_sharesansar_floorsheet_scraper(self):
    logger.info("Celery Task Started: Sharesansar Floorsheet Scraper")
    try:
        symbols = CompanyProfile.objects.values_list('symbol', flat=True)
        for symbol in symbols:
            logger.info(f"Celery: Processing for {symbol}")
            scraper = SharesansarFloorsheetScraper(symbol=symbol, headless=True)
            floorsheet_data = scraper.fetch_floorsheet()
            logger.info(f"Celery: Floorsheet Data Scraped for {symbol}")
            store_floorsheet_to_db_ss(symbol, floorsheet_data)
            logger.info(f"Celery: Data saved for {symbol}")
        return "Celery Task Executed"
    except Exception as e:
        logger.error(f"Error in run_sharesansar_floorsheet_scraper: {e}")
        return "Error in Celery Task: run_sharesansar_floorsheet_scraper"
    
@shared_task(bind=True)
def run_merolagani_floorsheet_scraper(self):
    logger.info("Celery Task Started: Merolagani Floorsheet Scraper")
    try:
        symbols = CompanyProfile.objects.values_list('symbol', flat=True)
        for symbol in symbols:
            logger.info(f"Celery: Processing for {symbol}")
            scraper = MerolaganiFloorsheetScraper(headless=True)
            floorsheet_data = scraper.run_scraper(symbol=symbol)
            logger.info(f"Celery: Floorsheet Data Scraped for {symbol}")
            store_floorsheet_to_db_ml(symbol, floorsheet_data)
            logger.info(f"Celery: Data saved for {symbol}")
        return "Celery Task Executed"
    except Exception as e:
        logger.error(f"Error in run_merolagani_floorsheet_scraper: {e}")
        return "Error in Celery Task: run_merolagani_floorsheet_scraper"

@shared_task(bind=True)
def run_nepstock_floorsheet_scraper(self):
    logger.info("Celery Task Started: Nepstock Floorsheet Scraper")
    try:
        symbols = CompanyProfile.objects.values_list('symbol', flat=True)
        for symbol in symbols:
            logger.info(f"Celery: Processing for {symbol}")
            floorsheet_data = scrape_company_floorsheet_nepstock(symbol, headless=True)
            logger.info(f"Celery: Floorsheet Data Scraped for {symbol}")
            store_floorsheet_to_db_ss(symbol, floorsheet_data)
            logger.info(f"Celery: Data saved for {symbol}")
        return "Celery Task Executed"
    except Exception as e:
        logger.error(f"Error in run_nepstock_floorsheet_scraper: {e}")
        return "Error in Celery Task: run_nepstock_floorsheet_scraper"
    
@shared_task(bind=True)
def run_merolagani_news_scraper(self):
    logger.info("Celery Task Started: Merolagani News Scraper")

    scraper = None
    try:
        scraper = MerolaganiNewsScraper(headless=True, max_records=8)
        records = scraper.fetch_news()
        logger.info(f"Celery: Fetched {len(records)} news items from listing page")

        detailed_records = scraper._extract_news_body(records=records)
        logger.info("Celery: News bodies extracted")

        store_news_to_db_ml(news_data=detailed_records)
        logger.info("Celery: News successfully stored to DB")

        return "Celery: Merolagani news scraping completed successfully"
    except Exception as e:
        logger.exception("Celery: Error during Merolagani news scraping task:")
        raise self.retry(exc=e, countdown=60, max_retries=3)  # Optional retry mechanism
    finally:
        if scraper:
            scraper.close()