from typing import Literal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time
import logging
logger = logging.getLogger("tms")

class SeleniumTMSClient:
    def __init__(self, broker_number, headless=False):
        self.broker_number = broker_number
        self.username = None
        self.password = None
        self.driver = self._init_driver(headless)
        self.login_url = f"https://tms{self.broker_number}.nepsetms.com.np/login"
        self.order_url = f"https://tms{self.broker_number}.nepsetms.com.np/tms/me/memberclientorderentry"

    def _init_driver(self, headless):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=options)

    def open_login_page(self):
        self.driver.get(self.login_url)
        time.sleep(2)

    def get_captcha_base64(self):
        captcha_img = self.driver.find_element(By.TAG_NAME, "img")
        return captcha_img.screenshot_as_base64

    def fill_credentials(self, username, password):
        self.username = username
        self.password = password

    def submit_login(self, captcha_text):
        self.driver.find_element(By.XPATH, "//input[@placeholder='Client Code/ User Name']").send_keys(self.username)
        self.driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(self.password)
        self.driver.find_element(By.ID, "captchaEnter").send_keys(captcha_text)
        self.driver.find_element(By.XPATH, "//input[@type='submit']").click()
        time.sleep(3)

    def login_successful(self):
        return "dashboard" in self.driver.current_url

    def get_new_captcha(self):
        return self.get_captcha_base64()

    def close(self):
        self.driver.quit()
    
    def scrape_dashboard_stats(self):
        data = {
            "turnover": "",
            "traded_shares": "",
            "transactions": "",
            "scrips": ""
        }

        try:
            wait = WebDriverWait(self.driver, 15)

            # Wait until the card with the header "Market Summary" is visible
            market_summary_card = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='card-title h5' and text()='Market Summary']/ancestor::div[contains(@class, 'card')]")
                )
            )

            # Scrape the total turnover (inside h4)
            turnover = market_summary_card.find_element(By.CLASS_NAME, "h4").text.strip()
            data["turnover"] = turnover

            # Get all three key stats
            figures = market_summary_card.find_elements(By.CLASS_NAME, "figure")

            if len(figures) >= 3:
                data["traded_shares"] = figures[0].find_element(By.CLASS_NAME, "figure-value").text.strip()
                data["transactions"] = figures[1].find_element(By.CLASS_NAME, "figure-value").text.strip()
                data["scrips"] = figures[2].find_element(By.CLASS_NAME, "figure-value").text.strip()
            else:
                print("⚠️ Not enough figure elements found.")

        except Exception as e:
            print("Error scraping dashboard:", e)
            self.driver.save_screenshot("scrape_error.png")  # Help debug

        return data

    def go_to_market_depth(self):
        try:
            wait = WebDriverWait(self.driver, 10)

            # Step 1: Click "Market Data"
            market_data_menu = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[.//span[contains(text(), 'Market Data')]]")
            ))
            market_data_menu.click()

            # Step 2: Wait for and click "Market Depth"
            market_depth_link = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//li[contains(@class, 'menu__dropdown')]//a[.//span[contains(text(), 'Market  Depth')]]")
            ))
            market_depth_link.click()

            print("✅ Navigated to Market Depth")

            return True

        except TimeoutException:
            print("❌ Could not navigate to Market Depth")
            self.driver.save_screenshot("market_depth_error.png")
            return False

    def get_market_depth_html(self, instrument_type: str, script_name: str) -> str:
        try:
            wait = WebDriverWait(self.driver, 15)

            # Step 1: Go to Market Depth
            self.go_to_market_depth()

            # Step 2: Select Instrument Type
            instrument_dropdown = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "select[formcontrolname='instrumentType']")
            ))
            select = Select(instrument_dropdown)
            select.select_by_visible_text(instrument_type.upper())
            print(f"✅ Selected Instrument Type: {instrument_type}")

            time.sleep(2)  # allow scripts to reload based on instrument

            # Step 3: Search and Select Script
            search_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ng-select[formcontrolname='security'] input[type='text']"))
            )
            search_input.click()
            search_input.clear()
            search_input.send_keys(script_name)
            time.sleep(2)  # wait for dropdown options to appear

            search_input.send_keys(Keys.ENTER)  # select top option
            print(f"✅ Selected Script: {script_name}")

            # Step 4: Wait for market depth table to load
            table = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.market__depth__general-info"))
            )
            print("✅ Market depth table loaded")

            return table.get_attribute("outerHTML")

        except TimeoutException as e:
            print("❌ Failed to load market depth")
            self.driver.save_screenshot("market_depth_failed.png")
            return "<p>Error: Could not retrieve market depth</p>"

    def go_to_place_order(self, script_name, transaction: Literal['Buy', 'Sell']):
        try:
            if transaction not in ('Buy', 'Sell'):
                raise ValueError("Transaction must be either 'Buy' or 'Sell'")
            self.order_url += f"?symbol={script_name}&transaction={transaction}"
            self.driver.get(self.order_url)
            time.sleep(2)
        except Exception as e:
            print(f"Failed to navigate to place order page: {e}")
            self.driver.save_screenshot("place_order_failed.png")
            return False
