from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException

import time
from datetime import datetime
import logging

from .base_scraper import BaseStockScraper

logger = logging.getLogger('stocks')

class SharesansarScraper(BaseStockScraper):
    def __init__(self, symbol, headless=False):
        super().__init__(headless=headless)
        self.symbol = symbol
        self.base_url = f"https://www.sharesansar.com/company/{self.symbol}"
    
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
        self.records = []
        try:
            self.driver.get(self.base_url)
            self.dismiss_alert_if_present()

            #price_history_tab = self.driver.find_element(By.ID, "btn_cpricehistory")
            price_history_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "btn_cpricehistory"))
            )
            price_history_tab.click()
            time.sleep(3)

            table = self.driver.find_element(By.ID, "myTableCPriceHistory")
            rows = table.find_elements(By.TAG_NAME, "tr")

            for i, row in enumerate(rows):
                if max_records and i >= max_records:
                    break
                cols = row.find_elements(By.TAG_NAME, "td")
                if cols:
                    try:
                        date = cols[1].text.strip()
                        open_price = cols[2].text.strip()
                        high_price = cols[3].text.strip()
                        low_price = cols[4].text.strip()
                        close_price = cols[5].text.strip()

                        date_obj = datetime.strptime(date, "%Y-%m-%d").date()

                        record = {
                            "Date": str(date_obj),
                            "Open": open_price,
                            "High": high_price,
                            "Low": low_price,
                            "Close": close_price,
                        }
                        self.records.append(record)
                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")
        except Exception as e:
            logger.error(f"Error fetching price history for {self.symbol}: {e}")
        finally:
            self.driver.quit()

        logger.info(f"Scraped {len(self.records)} records for {self.symbol} from ShareSansar")
        return self.records