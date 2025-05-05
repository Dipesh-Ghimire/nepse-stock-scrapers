from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

import pandas as pd
import time
from stockmarket import settings
from stocks.models import CompanyProfile, PriceHistory
import logging
logger = logging.getLogger('stocks')

class MerolaganiStockScraper:
    def __init__(self, symbol, headless=True, chromedriver_path=settings.CHROMEDRIVER_PATH):
        self.symbol = symbol
        self.base_url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}"
        self.records = []
        self.timeout = 15
        self.chromedriver_path = chromedriver_path
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless):
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options = webdriver.ChromeOptions()
        prefs = {"profile.default_content_setting_values.notifications": 2}
        options.add_experimental_option("prefs", prefs)

        service = Service(self.chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def dismiss_alert_if_present(self):
        try:
            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            logger.info(f"⚠ Dismissing alert: {alert.text}")
            alert.dismiss()  # or alert.accept()
        except NoAlertPresentException:
            logger.info(" No alert present.")
        except Exception as e:
            logger.info(f"⚠ Error while handling alert: {e}")

    def fetch_price_history(self, max_records):
        try:
            self.driver.get(self.base_url)
            self.dismiss_alert_if_present()
            # Wait for the price history tab and click it
            price_history_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_CompanyDetail1_lnkHistoryTab"))
            )
            price_history_tab.click()
            self.dismiss_alert_if_present()
            # Wait for the table to load
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
            logger.info(f" Fetched {len(self.records)} records for {self.symbol}")
            return self.records
        except Exception as e:
            print(f" Error fetching price history: {e}")
            return []
        finally:
            self.driver.quit()

    def save_to_csv(self, filename=None):
        if not self.records:
            print("⚠ No data to save.")
            return
        if not filename:
            filename = f"{self.symbol}_merolagani_history.csv"
        df = pd.DataFrame(self.records)
        df.to_csv(filename, index=False)
        print(f"📁 Data saved to {filename}")

def save_price_history_to_db_ml(symbol, price_history_data):
    """
    Save Merolagani price history data to the Django DB.
    """
    try:
        company = CompanyProfile.objects.get(symbol=symbol)
    except CompanyProfile.DoesNotExist:
        print(f" Company with symbol '{symbol}' not found in DB.")
        return

    for record in price_history_data:
        try:
            # Convert date from YYYY/MM/DD to Python date
            date_obj = datetime.strptime(record["Date"], "%Y/%m/%d").date()

            if PriceHistory.objects.filter(company=company, date=date_obj).exists():
                logger.info(f"⚠ Already exists: {symbol} - {record['Date']}")
                continue

            price_entry = PriceHistory(
                company=company,
                date=date_obj,
                open_price=record["Open"],
                high_price=record["High"],
                low_price=record["Low"],
                close_price=record["LTP"],
            )
            price_entry.save()
            logger.info(f" Saved: {symbol} - {record['Date']}")

        except Exception as e:
            print(f" Error saving record {record}: {str(e)}")
# Example usage
if __name__ == "__main__":
    scraper = MerolaganiStockScraper(symbol="SARBTM", headless=False)
    data = scraper.fetch_price_history(max_records=20)
    scraper.save_to_csv()
