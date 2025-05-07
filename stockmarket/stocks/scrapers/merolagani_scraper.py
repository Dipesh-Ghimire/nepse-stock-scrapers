from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
import time
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('stocks')

class MerolaganiScraper(BaseScraper):
    def __init__(self, symbol, headless=False):
        super().__init__(headless=headless)
        self.symbol = symbol
        self.base_url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}"

    def dismiss_alert_if_present(self):
        try:
            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            logger.info(f"⚠ Dismissing alert: {alert.text}")
            alert.dismiss()
        except NoAlertPresentException:
            logger.info("No alert present.")
        except Exception as e:
            logger.info(f"⚠ Error handling alert: {e}")

    def fetch_price_history(self, max_records=20):
        try:
            self.driver.get(self.base_url)
            self.dismiss_alert_if_present()

            price_history_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_CompanyDetail1_lnkHistoryTab"))
            )
            price_history_tab.click()
            self.dismiss_alert_if_present()

            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered"))
            )
            time.sleep(1)

            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table-bordered tbody tr")

            for i, row in enumerate(rows):
                if i >= max_records:
                    break
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 9:
                    self.records.append({
                        "SN": cols[0].text.strip(),
                        "Date": cols[1].text.strip(),
                        "LTP": cols[2].text.strip().replace(",", ""),
                        "% Change": cols[3].text.strip(),
                        "High": cols[4].text.strip().replace(",", ""),
                        "Low": cols[5].text.strip().replace(",", ""),
                        "Open": cols[6].text.strip().replace(",", ""),
                        "Qty": cols[7].text.strip().replace(",", ""),
                        "Turnover": cols[8].text.strip().replace(",", "")
                    })
            logger.info(f"Fetched {len(self.records)} records for {self.symbol}")
            return self.records
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []
        finally:
            self.close()

class MerolaganiFloorsheetScraper(BaseScraper):
    def __init__(self, headless=False):
        super().__init__(headless=headless)
        self.base_url = "https://merolagani.com/Floorsheet.aspx"
        logger.info("Initialized Merolagani Floorsheet Scraper.")
    def dismiss_alert_if_present(self):
        try:
            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            logger.info(f"⚠ Dismissing alert: {alert.text}")
            alert.dismiss()
        except NoAlertPresentException:
            logger.info("No alert present.")
        except Exception as e:
            logger.info(f"⚠ Error handling alert: {e}")
    def extract_date(self):
        try:
            logger.info("Extracting date from the page...")
            self.driver.get(self.base_url)

            # Wait for the date element to load
            market_date_element = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_marketDate"))
            )

            # Extract date from the span tag
            date_text = market_date_element.text.strip()
            date_str = date_text.split("As of")[-1].strip().split()[0]  # Extract date part only
            logger.info(f"Extracted date: {date_str}")
            return date_str
        except Exception as e:
            logger.error(f"Error extracting date: {e}")
            return None

    def search_floorsheet(self, symbol, date):
        try:
            # Enter the symbol into the symbol input box
            symbol_input = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ASCompanyFilter_txtAutoSuggest"))
            )
            symbol_input.clear()
            symbol_input.send_keys(symbol)

            # Enter the date into the date input box (format MM/DD/YYYY)
            date_input = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtFloorsheetDateFilter")
            date_input.clear()
            date_input.send_keys(date)

            # Click the search button
            search_button = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lbtnSearchFloorsheet")
            search_button.click()

            self.dismiss_alert_if_present()
            # Wait for processing to complete
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered"))
            )
            logger.info("Search completed and table is loaded.")
        except Exception as e:
            logger.error(f"Error performing search: {e}")

    def scrape_floorsheet_data(self, date_str):
        try:
            # Wait for the table to load
            rows = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.table-bordered tbody tr"))
            )
            
            floorsheet_data = []
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 8:
                    floorsheet_data.append({
                        "Transact. No.": cols[1].text.strip(),
                        "Symbol": cols[2].text.strip(),
                        "Buyer": cols[3].text.strip(),
                        "Seller": cols[4].text.strip(),
                        "Quantity": cols[5].text.strip(),
                        "Rate": cols[6].text.strip(),
                        "Amount": cols[7].text.strip(),
                        "Date": date_str
                    })
            logger.info(f"Scraped {len(floorsheet_data)} records.")
            return floorsheet_data
        except Exception as e:
            logger.error(f"Error scraping floorsheet data: {e}")
            return []

    def run_scraper(self, symbol):
        date = self.extract_date()
        if date:
            self.search_floorsheet(symbol, date)
            return self.scrape_floorsheet_data(date_str = date)
        return []

if __name__ == "__main__":
    scraper = MerolaganiFloorsheetScraper(headless=True)
    data = scraper.run_scraper("MEN")
    print(data)
