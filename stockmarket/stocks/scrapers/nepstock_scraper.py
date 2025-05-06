from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('stocks')

class NepalstockScraper(BaseScraper):
    def __init__(self, headless=True):
        super().__init__(headless=headless)
        self.base_url = "https://www.nepalstock.com"
        self.search_delay = 2

    def search_company(self, symbol):
        try:
            self.driver.get(self.base_url)
            time.sleep(1)
            search_input = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".header__search--wrap input"))
            )
            search_input.clear()
            search_input.send_keys(symbol)
            search_input.send_keys(Keys.RETURN)
            time.sleep(self.search_delay)

            company_link = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//a[contains(., '{symbol}')]"))
            )
            url = company_link.get_attribute('href')
            self.driver.get(url)
            logger.info(f"🔍 Navigated to {url}")
            return True
        except Exception as e:
            logger.error(f" Error searching for company {symbol}: {e}")
            return False

    def click_price_history_tab(self):
        try:
            price_history_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#pricehistory-tab"))
            )
            price_history_tab.click()

            WebDriverWait(self.driver, self.timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.tab-pane.active#pricehistorys"))
            )
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f" Error clicking Price History tab: {e}")
            return False

    def scrape_current_page(self):
        try:
            price_history_div = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, "pricehistorys"))
            )
            table = price_history_div.find_element(By.CSS_SELECTOR,
                "table.table.table__lg.table-striped.table__border.table__border--bottom")
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 13:
                    self.records.append({
                        'SN': cols[0].text.strip(),
                        'Date': cols[1].text.strip(),
                        'Open': cols[2].text.strip().replace(',', ''),
                        'High': cols[3].text.strip().replace(',', ''),
                        'Low': cols[4].text.strip().replace(',', ''),
                        'Close': cols[5].text.strip().replace(',', ''),
                        'TTQ': cols[6].text.strip().replace(',', ''),
                        'TT': cols[7].text.strip().replace(',', ''),
                        'Previous Close': cols[8].text.strip().replace(',', ''),
                        '52 Week High': cols[9].text.strip().replace(',', ''),
                        '52 Week Low': cols[10].text.strip().replace(',', ''),
                        'Total Trades': cols[11].text.strip().replace(',', ''),
                        'ATP': cols[12].text.strip().replace(',', '')
                    })
            logger.info(f" Scraped {len(self.records)} records from page")
            return True
        except Exception as e:
            logger.error(f" Error scraping page: {e}")
            return False

    def go_to_next_page(self):
        try:
            next_button = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.pagination-next a"))
            )
            next_button.click()
            time.sleep(3)
            return True
        except Exception as e:
            logger.info("🔚 No next page or error navigating")
            return False

    def scrape_all_pages(self, max_pages=5):
        try:
            page = 1
            while page <= max_pages:
                if not self.scrape_current_page():
                    break
                if not self.go_to_next_page():
                    break
                page += 1
            logger.info(f" Finished scraping {len(self.records)} records across {page} pages")
        finally:
            self.close()

def scrape_company_price_history_nepstock(symbol, max_pages=2, output_csv=False):
    scraper = NepalstockScraper(headless=True)
    try:
        if scraper.search_company(symbol):
            if scraper.click_price_history_tab():
                scraper.scrape_all_pages(max_pages=max_pages)
                if output_csv:
                    scraper.save_to_csv(f"{symbol}_price_history.csv")
                return scraper.records
    finally:
        scraper.close()
    return []