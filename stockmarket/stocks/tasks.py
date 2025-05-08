from celery import shared_task
from .utility import save_price_history_to_db, save_price_history_to_db_ss, save_price_history_to_db_ml
from .scrapers.sharesansar_scraper import SharesansarScraper
from .scrapers.merolagani_scraper import MerolaganiScraper
from .scrapers.nepstock_scraper import scrape_company_price_history_nepstock
from .models import CompanyProfile

import logging
logger = logging.getLogger('stocks')

@shared_task(bind=True)
def run_sharesansar_pricehistory_scraper(self):
    logger.info("Celery Task Started: Sharesansar Price History Scraper")
    symbols = CompanyProfile.objects.values_list('symbol', flat=True)
    for symbol in symbols:
        logger.info(f"Celery: Processing for {symbol}")
        scraper = SharesansarScraper(symbol=symbol, headless=True)
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