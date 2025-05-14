from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from ..models import CompanyNews
from dateutil import parser as date_parser
from django.utils.timezone import make_aware, is_naive

from ..utility import get_latest_data_of_pricehistory, get_latest_ss_news_date
import time
from datetime import datetime
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('stocks')

class SharesansarPriceScraper(BaseScraper):
    def __init__(self, symbol, headless=False):
        super().__init__(headless=headless)
        self.symbol = symbol
        self.base_url = f"https://www.sharesansar.com/company/{self.symbol}"
        self.wait = WebDriverWait(self.driver, self.timeout)

    def fetch_price_history(self, max_records=9999):

        self.records = []
        logger.info(f"Started Scraping price history for {self.symbol} from ShareSansar")

        try:
            self.driver.get(self.base_url)

            price_history_tab = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btn_cpricehistory"))
            )
            price_history_tab.click()
            time.sleep(1)
            latest_data = get_latest_data_of_pricehistory(self.symbol)
            keep_scraping = True
            while keep_scraping:
                table = self.wait.until(
                    EC.presence_of_element_located((By.ID, "myTableCPriceHistory"))
                )
                rows = table.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if cols:
                        try:
                            date = cols[1].text.strip()
                            open_price = cols[2].text.strip()
                            high_price = cols[3].text.strip()
                            low_price = cols[4].text.strip()
                            close_price = cols[5].text.strip()

                            date_obj = datetime.strptime(date, "%Y-%m-%d").date()

                            if date_obj.year < 2025:
                                keep_scraping = False
                                break  # Stop scraping if older than 2025

                            record = {
                                "Date": str(date_obj),
                                "Open": open_price,
                                "High": high_price,
                                "Low": low_price,
                                "Close": close_price,
                            }
                            self.records.append(record)

                            if max_records and len(self.records) >= max_records:
                                keep_scraping = False
                                break
                            if latest_data is not None and latest_data >= date_obj:
                                keep_scraping = False
                                logger.info("Latest data in DB is newer than scraped data, stopping.")
                                break
                        except Exception as e:
                            logger.warning(f"Error parsing row: {e}")

                # Click 'Next' if still scraping
                if keep_scraping:
                    try:
                        next_btn = self.driver.find_element(By.ID, "myTableCPriceHistory_next")
                        # Stop if next button is disabled
                        if "disabled" in next_btn.get_attribute("class"):
                            break
                        self.driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(1)
                    except NoSuchElementException:
                        logger.info("Next button not found, ending pagination.")
                        break

        except Exception as e:
            logger.error(f"Error fetching price history for {self.symbol}: {e}")
        finally:
            self.driver.quit()

        logger.info(f"Scraped {len(self.records)} records for {self.symbol} from ShareSansar")
        return self.records

class SharesansarFloorsheetScraper(BaseScraper):
    def __init__(self, symbol, headless=False):
        super().__init__(headless=headless)
        self.symbol = symbol
        self.base_url = f"https://www.sharesansar.com/company/{self.symbol}"
        self.wait = WebDriverWait(self.driver, self.timeout)
    
    def fetch_floorsheet(self):
        floorsheet = []
        logger.info(f"Started Scraping floorsheet for {self.symbol} from ShareSansar")
        try:
            self.driver.get(self.base_url)

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
    
class SharesansarNewsScraper(BaseScraper):
    def __init__(self, headless=False, max_records=9999):
        super().__init__(headless=headless)
        self.base_url = "https://www.sharesansar.com/category/latest"
        self.wait = WebDriverWait(self.driver, self.timeout)
        self.max_records = max_records
        self.records = []
        self.stop_flag = False

    def _close_ads(self):
        try:
            # Wait a very short time for the ad to appear
            close_button = WebDriverWait(self.driver, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-red[data-dismiss='modal']"))
            )
            close_button.click()
            print("[INFO] Ad closed.")
        except TimeoutException:
            # Ad not present, ignore silently
            pass
        except (ElementClickInterceptedException, NoSuchElementException) as e:
            print(f"[WARN] Failed to close ad: {e}")

    def fetch_news(self):
        self.records = []
        logger.info("Started scraping news from ShareSansar")

        try:
            self.driver.get(self.base_url)
            keep_scraping = True

            latest_db_date = get_latest_ss_news_date()
            while keep_scraping and not self.stop_flag:
                # Scrape news list
                news_list = self.scrape_news_list()
                logger.info(f"Scraped {len(news_list)} news items from the news list page.")
                if not news_list:
                    logger.info("No new news found on this page.")
                    break

                # Loop over each news item and scrape its details
                for news in news_list:
                    news_url = news["news_url"]
                    if self.is_news_scraped(news_url):
                        logger.info(f"Skipping already scraped news: {news_url}")
                        continue

                    news_body, news_image, news_date = self.scrape_news_details(news_url)
                    # Make naive datetimes timezone-aware
                    if is_naive(news_date):
                        scraped_date = make_aware(news_date)

                    if latest_db_date and is_naive(latest_db_date):
                        latest_db_date = make_aware(latest_db_date)

                    if latest_db_date and scraped_date and scraped_date <= latest_db_date:
                        self.stop_flag = True
                        logger.info("Latest news in DB is newer than scraped data, stopping.")
                    news_record = {
                            "news_url": news_url,
                            "news_title": news["news_title"],
                            "news_date": news_date,
                            "news_body": news_body,
                            "news_image": news_image
                        }
                    self.records.append(news_record)

                    if len(self.records) >= self.max_records:
                        keep_scraping = False
                        break

                # Click 'Next' to navigate to the next page
                if keep_scraping:
                    keep_scraping = self.paginate()

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            self.driver.quit()

        logger.info(f"Scraped {len(self.records)} news articles.")
        return self.records

    def scrape_news_list(self):
        news_list = []
        try:
            # Wait for the news section to load
            news_section = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".featured-news-list")))
            # iternate until max_records
            for item in news_section[:self.max_records]:
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, "h4.featured-news-title")
                    link_element = item.find_element(By.TAG_NAME, "a")
                    # date_element = item.find_element(By.CSS_SELECTOR, "span.text-org")
                    date_element = WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.text-org")))

                    news_url = link_element.get_attribute("href")
                    news_title = title_element.text.strip()
                    news_date = date_element.text.strip()

                    logger.info(f"News Title: {news_title}")
                    # Parse the date (e.g., "Monday, May 12, 2025")
                    news_date_obj = datetime.strptime(news_date, "%A, %B %d, %Y").date()

                    news_list.append({
                        "news_url": news_url,
                        "news_title": news_title,
                        "news_date": news_date_obj
                    })
                except Exception as e:
                    logger.warning(f"Error scraping news item: {e}")
        except Exception as e:
            logger.error(f"Error scraping news list: {e}")
        return news_list

    def scrape_news_details(self, news_url):
        news_body = None
        news_image = None
        news_date = None

        try:
            self.driver.get(news_url)
            self._close_ads()  # Close any ads that may appear
            content_section = self.wait.until(EC.presence_of_element_located((By.ID, "newsdetail-content")))
            news_body = content_section.text.strip()
            # ✅ Try finding image in <figure class="newsdetail">
            try:
                image_element = self.driver.find_element(By.CSS_SELECTOR, "figure.newsdetail img")
                news_image = image_element.get_attribute("src")
            except NoSuchElementException:
                # ✅ If not found, try finding image inside #newsdetail-content
                try:
                    image_element = content_section.find_element(By.TAG_NAME, "img")
                    news_image = image_element.get_attribute("src")
                except NoSuchElementException:
                    logger.info(f"No image found for {news_url}")

            try:
                date_element = self.driver.find_element(By.CSS_SELECTOR, ".margin-bottom-10 h5")
                date_text = date_element.text.strip()

                # Example text: "Tue, May 13, 2025 10:20 AM on Latest, Corporate"
                date_part = date_text.split(" on ")[0].strip()  # Take only "Tue, May 13, 2025 11:14 AM"
                news_date = date_parser.parse(date_part)
            except Exception as e:
                logger.warning(f"No date found or parsing error at {news_url}: {e}")



        except Exception as e:
            logger.warning(f"Error scraping news details from {news_url}: {e}")

        return news_body, news_image, news_date

    def is_news_scraped(self, news_url):
        # Check if news URL is already scraped and exists in the database
        return CompanyNews.objects.filter(news_url=news_url).exists()

    def paginate(self):
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, "ul.pagination li.page-item a")
            next_url = next_button.get_attribute("href")
            if next_url:
                self.driver.get(next_url)
                time.sleep(2)
                return True
            else:
                return False
        except NoSuchElementException:
            logger.info("No more pages to scrape.")
            return False

if __name__== "__main__":
    news_scraper = SharesansarNewsScraper(headless=False, max_records=8)
    news_records = news_scraper.fetch_news()
    news_scraper.close()
    for record in news_records:
        print(f"Title: {record.news_title}, URL: {record.news_url}, Date: {record.news_date}")
    
