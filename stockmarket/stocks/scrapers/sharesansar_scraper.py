from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.support.ui import Select

import time
from datetime import datetime
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('stocks')

class SharesansarScraper(BaseScraper):
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
    
    def fetch_floorsheet(self):
        floorsheet = []

        try:
            self.driver.get(self.base_url)
            self.dismiss_alert_if_present()

            # Step 1: Click the Floorsheet tab
            floorsheet_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "btn_cfloorsheet"))
            )
            floorsheet_tab.click()
            time.sleep(2)

            # Step 2: Set dropdown to 500 entries
            select_elem = Select(WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.NAME, "myTableCFloorsheet_length"))
            ))
            select_elem.select_by_value("500")
            time.sleep(2)

            while True:
                # Step 3: Scrape table rows
                rows = self.driver.find_elements(By.CSS_SELECTOR, "#myTableCFloorsheet tbody tr")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if cols and len(cols) >= 8:
                        try:
                            transaction_id = cols[1].text.strip()
                            buyer = int(cols[2].text.strip())
                            seller = int(cols[3].text.strip())
                            quantity = float(cols[4].text.strip().replace(",", ""))
                            rate = float(cols[5].text.strip().replace(",", ""))
                            amount = float(cols[6].text.strip().replace(",", ""))
                            date_str = cols[7].text.strip()
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                            record = {
                                "transaction_id": transaction_id,
                                "buyer": buyer,
                                "seller": seller,
                                "quantity": quantity,
                                "rate": rate,
                                "amount": amount,
                                "date": date_obj,
                            }
                            floorsheet.append(record)
                        except Exception as e:
                            logger.warning(f"Error parsing row: {e}")

                # Step 4: Click next if not disabled
                try:
                    next_btn = self.driver.find_element(By.ID, "myTableCFloorsheet_next")
                    if "disabled" in next_btn.get_attribute("class"):
                        break
                    next_btn.click()
                    time.sleep(2)
                except Exception:
                    break

        except Exception as e:
            logger.error(f"Error fetching floorsheet for {self.symbol}: {e}")
        finally:
            self.driver.quit()

        logger.info(f"Scraped {len(floorsheet)} floorsheet records for {self.symbol} from ShareSansar")
        return floorsheet
