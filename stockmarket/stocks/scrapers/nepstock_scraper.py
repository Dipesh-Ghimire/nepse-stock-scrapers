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
    

    #Floorsheet
    def click_floorsheet_tab(self):
        try:
            floorsheet_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "floorsheet-tab"))
            )
            floorsheet_tab.click()
            logger.info("📄 Clicked on Floorsheet tab")
            time.sleep(1)  # Allow content to load
            return True
        except Exception as e:
            logger.error(f"Failed to click Floorsheet tab: {e}")
            return False

    def select_items_per_page(self, count=500):
        try:
            select_element = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".table__perpage select"))
            )
            select_element.click()
            option = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f".table__perpage select option[value='{count}']"))
            )
            option.click()
            logger.info(f"📊 Set items per page to {count}")
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Failed to select items per page ({count}): {e}")
            return False

    def click_filter_button(self):
        try:
            wait = WebDriverWait(self.driver, self.timeout)

            # Wait until the filter button is visible and clickable
            filter_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.box__filter--search"))
            )
            wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.box__filter--search"))
            )

            logger.debug("Filter button located")

            # Scroll into view just in case
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_button)

            # Get count of rows before click (to detect update after)
            initial_rows = len(self.driver.find_elements(By.CSS_SELECTOR, "table.table-striped tbody tr"))

            # Click using JS for reliability
            self.driver.execute_script("arguments[0].click();", filter_button)

            logger.info("Clicked Filter button")

            wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "table.table-striped tbody tr")) != initial_rows)
            time.sleep(3)  # Allow table to reload
            return True

        except Exception as e:
            logger.error(f"Failed to click Filter button: {e}")
            return False

    def scrape_floorsheet_data(self):
        floorsheet_data = []
        page_count = 1
        wait = WebDriverWait(self.driver, self.timeout)

        while True:
            try:
                # Wait for at least one row in the table
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped tbody tr")))

                rows = self.driver.find_elements(By.CSS_SELECTOR, "table.table-striped tbody tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 7:
                        record = {
                            "SN": cols[0].text.strip(),
                            "Contract No": cols[1].text.strip(),
                            "Buyer No": cols[2].text.strip(),
                            "Seller No": cols[3].text.strip(),
                            "Quantity": cols[4].text.strip(),
                            "Rate": cols[5].text.strip(),
                            "Amount": cols[6].text.strip()
                        }
                        floorsheet_data.append(record)

                logger.info(f"📄 Scraped page {page_count} with {len(rows)} rows")

                # Check if 'Next' button is disabled
                pagination = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.ngx-pagination")))
                next_li = pagination.find_element(By.CLASS_NAME, "pagination-next")

                if "disabled" in next_li.get_attribute("class"):
                    break  # Last page

                next_button = next_li.find_element(By.TAG_NAME, "a")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)

                # Wait for the next button to be clickable specifically
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.ngx-pagination .pagination-next a")))
                next_button.click()

                page_count += 1
                time.sleep(2)  # Let the table reload

            except Exception as e:
                logger.error(f"Error scraping floorsheet or paginating: {e}")
                break

        return floorsheet_data


def scrape_company_floorsheet_nepstock(company_symbol: str, headless: bool = True):
    scraper = NepalstockScraper(headless=headless)
    try:
        if not scraper.search_company(company_symbol):
            logger.error("Company search failed.")
            return

        if not scraper.click_floorsheet_tab():
            logger.error("Could not click floorsheet tab.")
            return

        if not scraper.select_items_per_page(500):
            logger.error("Could not select 500 items per page.")
            return

        if not scraper.click_filter_button():
            logger.error("Could not click filter button.")
            return
    finally:
        scraper.close()
    return scraper.scrape_floorsheet_data()

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