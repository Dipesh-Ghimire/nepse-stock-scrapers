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
