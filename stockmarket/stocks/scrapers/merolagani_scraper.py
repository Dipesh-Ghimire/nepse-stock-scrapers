from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, TimeoutException, NoSuchElementException
import time
from dateutil import parser as date_parser
from dateutil.parser import parse as parse_datetime
from django.utils import timezone
from django.utils.timezone import make_aware, is_naive
from ..models import CompanyNews
import logging
from datetime import time as dt_time

from ..utility import get_latest_news_date

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

class MerolaganiNewsScraper(BaseScraper):
    def __init__(self, max_records=20, headless=True):
        super().__init__(headless=headless)
        self.base_url = "https://merolagani.com/NewsList.aspx"
        self.max_records = max_records

    def dismiss_alert_if_present(self):
        try:
            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            if alert.dismiss():
                logger.info(f"⚠ Dismissing alert: {alert.text}")
        except NoAlertPresentException:
            logger.info("No alert present.")
        except Exception as e:
            logger.info(f"⚠ Error handling alert: {e}")
            
    def _close_ads(self):
        try:
            self.driver.execute_script("""
                var closeBtn = document.getElementById('close');
                if (closeBtn) closeBtn.click();
            """)
            logger.debug("✅ Programmatically clicked close button")
        except Exception as e:
            logger.debug(f"ℹ️ No close button found: {e}")
    
    def _click_load_more(self):
        try:
            # Wait until the button is present and clickable
            load_more = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-primary.btn-block"))
            )

            # Scroll into view to avoid overlap by other elements
            self.driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
            time.sleep(1)  # Let scrolling finish

            # Click using JavaScript to avoid click interception
            self.driver.execute_script("arguments[0].click();", load_more)

            self.dismiss_alert_if_present()
            logger.info("Clicked 'Load More' button.")
            time.sleep(2)  # Allow time for content to load

        except TimeoutException:
            logger.info("⚠️ 'Load More' button not found or not clickable.")
        except Exception as e:
            logger.error(f"Error clicking 'Load More': {e}")

    def _extract_recent_news_items(self):
        # Step 1: Extract the news items
        news_divs = self.driver.find_elements(By.CSS_SELECTOR, ".news-list .media-news")
        records = []
        stop_flag = False
        latest_db_date = get_latest_news_date()
        existing_urls = set(CompanyNews.objects.values_list("news_url", flat=True))
        if not latest_db_date:
            logger.info("No news records in DB, scraping all.")
        
        for div in news_divs[:self.max_records]:
            try:
                rows_loaded = len(self.driver.find_elements(By.CSS_SELECTOR, ".news-list .row"))
                logger.info(f"Rows loaded: {rows_loaded}")
                date = div.find_element(By.CSS_SELECTOR, ".media-label").text.strip()
                title_element = div.find_element(By.CSS_SELECTOR, ".media-title a")
                news_url = title_element.get_attribute("href")
                scraped_date = date_parser.parse(date)
                # Make naive datetimes timezone-aware
                if is_naive(scraped_date):
                    scraped_date = make_aware(scraped_date)

                if latest_db_date and is_naive(latest_db_date):
                    latest_db_date = make_aware(latest_db_date)

                # Only compare dates if latest_db_date exists
                if (latest_db_date is not None and scraped_date < latest_db_date) or news_url in existing_urls:
                    stop_flag = True
                    logger.info(f"⚠️ Skipping already scraped news item: {title_element.text.strip()}")
                    break  # Skip if already in DB

                title = title_element.text.strip()
                
                image = div.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                
                records.append({
                    "title": title,
                    "url": news_url,
                    "image": image,
                    "date": scraped_date
                })
                logger.info(f"📰 Extracted news item: {title}")
                logger.info(f"📰 URL: { news_url}")
                logger.info(f"📰 Image: {image}")
                logger.info(f"📰 Date: {scraped_date}")

                if rows_loaded*2 < self.max_records:
                    self._click_load_more()
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse a news item: {e}")
        return records
    
    def _extract_news_body(self, records):
        for record in records:
            try:    
                self.driver.get(record['url'])
                self._close_ads()
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_newsDetail"))
                )
                date = record["date"]
                # Make naive datetimes timezone-aware
                if is_naive(date):
                    date = make_aware(date)
                # Check if we need to update the time (only if original time was 00:00:00)
                if date.time() == dt_time(0, 0):
                    try:
                        time_element = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_newsDate.media-label")
                        time_text = time_element.text.strip()
                        detailed_date = date_parser.parse(time_text)
                        
                        # Make timezone aware if needed
                        if is_naive(detailed_date):
                            detailed_date = make_aware(detailed_date)
                        
                        record["date"] = detailed_date
                        logger.info(f"🕒 Updated time for {record['title']}: {detailed_date}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not update time from detail page: {e}")
                # Extract the overview paragraph first
                try:
                    overview_elem = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_newsOverview")
                    overview_p = overview_elem.find_element(By.TAG_NAME, "p").text.strip()
                except NoSuchElementException:
                    overview_p = ""

                # Now extract the main detail content
                detail_container = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_newsDetail")

                # Remove unwanted ad sections
                try:
                    ad_sections = detail_container.find_elements(By.CLASS_NAME, "news-inner-ads")
                    for ad in ad_sections:
                        self.driver.execute_script("""
                            var element = arguments[0];
                            element.parentNode.removeChild(element);
                        """, ad)
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove ads: {e}")

                # Extract visible paragraph text
                paragraphs = detail_container.find_elements(By.TAG_NAME, "p")
                body_paragraphs = [p.text.strip() for p in paragraphs if p.text.strip()]

                # Prepend the overview if available
                full_body = "\n\n".join([overview_p] + body_paragraphs if overview_p else body_paragraphs)

                record["body"] = full_body
                logger.info(f"📰 Body extracted for: {record['title']}")

            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"⚠ Failed to extract body from {record['url']} – {e}")
                record["body"] = ""
        return records

    def fetch_news(self):
        try:
            self.driver.get(self.base_url)
            total_rows_needed = self.max_records // 2
            time.sleep(2)

            # while True:
            #     rows_loaded = len(self.driver.find_elements(By.CSS_SELECTOR, ".news-list .row"))
            #     if rows_loaded >= total_rows_needed:
            #         break
            #     self._click_load_more()
            self._click_load_more()
            self.records = self._extract_recent_news_items()

            logger.info(f"Fetched {len(self.records)} news records.")
            return self.records

        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
        

if __name__ == "__main__":
    scraper = MerolaganiFloorsheetScraper(headless=True)
    data = scraper.run_scraper("MEN")
    print(data)
