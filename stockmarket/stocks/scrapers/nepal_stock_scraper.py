#!/usr/bin/env python3
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd

class NepalStockScraper:
    def __init__(self, headless=True):
        self.base_url = "https://www.nepalstock.com"
        self.timeout = 15
        self.search_delay = 2
        self.driver = self._init_driver(headless)
        self.price_history = []
    
    def _init_driver(self, headless):
        """Initialize Chrome driver with options"""
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        
        # Make scraping less detectable
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Update this path to your chromedriver location
        service = Service('/home/dipesh/Desktop/chromedriver-linux64/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def search_company(self, symbol):
        """Search for a company by symbol and return its detail page URL"""
        try:
            print(f"Searching for company with symbol: {symbol}")
            
            # Go to homepage
            self.driver.get(self.base_url)
            time.sleep(1)  # small delay for page load
            
            # Find search input and enter symbol
            search_input = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".header__search--wrap input"))
            )
            search_input.clear()
            search_input.send_keys(symbol)
            search_input.send_keys(Keys.RETURN)
            
            # Wait for search results
            time.sleep(self.search_delay)
            
            # Find the company link in search results
            company_link = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//a[contains(., '{symbol}')]"))
            )
            url = company_link.get_attribute('href')
            print(f"Found company URL: {url}")
            return url
            
        except Exception as e:
            print(f"Error searching for company {symbol}: {e}")
            return None
        
    def click_price_history_tab(self):
        """Click on the Price History tab"""
        try:
            price_history_tab = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#pricehistory-tab"))
            )
            price_history_tab.click()
            print("📊 Price History tab clicked")

            # Wait for price history content to be visible
            WebDriverWait(self.driver, self.timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.tab-pane.active#pricehistorys"))
            )
            time.sleep(2)  # Wait for table to load
            return True
        except Exception as e:
            print(f" Error clicking Price History tab: {str(e)}")
            return False

    # def scrape_current_page(self):
    #         """Scrape data from the current price history table"""
    #         try:
    #             table = WebDriverWait(self.driver, self.timeout).until(
    #                 EC.presence_of_element_located((By.CSS_SELECTOR, "div.table-responsive table"))
    #             )
                
    #             rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
    #             current_page_data = []
                
    #             for row in rows:
    #                 cols = row.find_elements(By.TAG_NAME, "td")
    #                 if len(cols) >= 13:  # Ensure we have all columns
    #                     data = {
    #                         'SN': cols[0].text.strip(),
    #                         'Date': cols[1].text.strip(),
    #                         'Open': cols[2].text.strip().replace(',', ''),
    #                         'High': cols[3].text.strip().replace(',', ''),
    #                         'Low': cols[4].text.strip().replace(',', ''),
    #                         'Close': cols[5].text.strip().replace(',', ''),
    #                         'TTQ': cols[6].text.strip().replace(',', ''),
    #                         'TT': cols[7].text.strip().replace(',', ''),
    #                         'Previous Close': cols[8].text.strip().replace(',', ''),
    #                         '52 Week High': cols[9].text.strip().replace(',', ''),
    #                         '52 Week Low': cols[10].text.strip().replace(',', ''),
    #                         'Total Trades': cols[11].text.strip().replace(',', ''),
    #                         'ATP': cols[12].text.strip().replace(',', '')
    #                     }
    #                     current_page_data.append(data)
                
    #             if current_page_data:
    #                 self.price_history.extend(current_page_data)  # Add to master list
    #                 print(f"📋 Scraped {len(current_page_data)} records from current page")
    #             else:
    #                 print("⚠️ No data found on current page")
                
    #             return True
    #         except Exception as e:
    #             print(f"❌ Error scraping table: {str(e)}")
    #             return False
    
    def scrape_current_page(self):
        """Scrape data from the current price history table using parent ID and table classes"""
        try:
            # First find the parent div with ID pricehistorys
            price_history_div = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, "pricehistorys"))
            )
            
            # Then find the table within this div with specific classes
            table = price_history_div.find_element(By.CSS_SELECTOR, 
                "table.table.table__lg.table-striped.table__border.table__border--bottom")
            
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            current_page_data = []
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 13:  # Ensure we have all columns
                    data = {
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
                    }
                    current_page_data.append(data)
            
            if current_page_data:
                self.price_history.extend(current_page_data)
                print(f"📋 Scraped {len(current_page_data)} records from current page")
            else:
                print("⚠️ No data found on current page")
            
            return True
            
        except TimeoutException:
            print("❌ Timeout waiting for price history table to load")
            return False
        except Exception as e:
            print(f"❌ Unexpected error scraping table: {str(e)}")
            return False
    def go_to_next_page(self):
        """Navigate to the next page of results"""
        try:
            next_button = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.pagination-next a"))
            )
            next_button.click()
            time.sleep(3)  # Wait for new page to load
            print(" Navigated to next page")
            return True
        except Exception as e:
            print(f" Error navigating to next page: {str(e)}")
            return False
    
    def scrape_all_pages(self, max_pages=10):
        """Scrape all available pages of price history"""
        try:
            page_count = 1
            while True:
                if not self.scrape_current_page():
                    break
                
                if page_count >= max_pages:
                    print(f"ℹReached maximum page limit ({max_pages})")
                    break
                
                if not self.go_to_next_page():
                    break
                
                page_count += 1
            
            print(f" Successfully scraped {len(self.price_history)} records from {page_count} pages")
            return True
        except Exception as e:
            print(f" Error during pagination: {str(e)}")
            return False
    
    def save_to_csv(self, filename):
        """Save scraped data to CSV file"""
        try:
            df = pd.DataFrame(self.price_history)
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f" Error saving to CSV: {str(e)}")
    
    def close(self):
        """Close the browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()

def main(): 
    scraper = NepalStockScraper(headless=False)
    try:
        if scraper.search_company("SARBTM"):
            if scraper.click_price_history_tab():
                scraper.scrape_all_pages(max_pages=2)
                print(scraper.price_history)
                scraper.save_to_csv("sarbtm_price_history.csv")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()