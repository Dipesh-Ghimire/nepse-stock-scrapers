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
logger = logging.getLogger("stocks")

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
                    (By.XPATH, "//div[contains(@class, 'card-title') and normalize-space(text())='Market Summary']/ancestor::div[contains(@class, 'card')]")
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
                logger.info("⚠️ Not enough figure elements found.")

        except Exception as e:
            logger.info("Error scraping dashboard: %s", e)
            self.driver.save_screenshot("scrape_error.png")  # Help debug

        return data

    def scrape_collateral(self):
        data = {
            "collateral_utilized": "",
            "collateral_available": ""
        }

        try:
            wait = WebDriverWait(self.driver, 15)

            # Wait until the "Collateral Utilized" label is present
            utilized_value_elem = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//span[contains(text(), 'Collateral Utilized')]/following-sibling::span"
                ))
            )
            data["collateral_utilized"] = utilized_value_elem.text.strip()

            # Wait until the "Collateral Available" label is present
            available_value_elem = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//a[@id='collateralView']//following-sibling::span"
                ))
            )
            data["collateral_available"] = available_value_elem.text.strip()

        except Exception as e:
            logger.info("Error scraping collateral data: %s", e)
            self.driver.save_screenshot("scrape_collateral_error.png")

        return data

    def execute_trade(self, script_name: str, transaction: Literal['Buy', 'Sell'], quantity: int, price: float):
        try:
            self.enter_trade_details(quantity, price)

            # Extract LTP
            ltp = self.extract_ltp()
            logger.info(f"Trade executing: {transaction} {script_name} at :{ltp}:")


            if transaction == 'Buy':
                self.click_buy_button()
            else:
                self.click_sell_button()

            # Wait briefly for the toast to appear
            wait = WebDriverWait(self.driver, 0.1)
            toast = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.toast-text.ng-star-inserted"))
            )

            # Extract toast title and message
            toast_title = toast.find_element(By.CSS_SELECTOR, "span.toast-title").text.strip()
            toast_msg = toast.find_element(By.CSS_SELECTOR, "span.toast-msg").text.strip()

            msg = self.wait_for_toast()
            if "Success" in msg:
                print("Trade executed successfully.")
            elif "INVALID_ORDER_QUANTITY" in msg or "Invalid quantity" in msg:
                print("Trade failed: Invalid quantity.")
            elif "Price should be within valid range" in msg:
                print("Trade failed: Price out of allowed range.")
            else:
                print("⚠️ Unknown toast message:", msg)

        except Exception as e:
            logger.info("Error executing trade: %s", e)
            self.driver.save_screenshot("trade_execution_error.png")

    def enter_trade_details(self, quantity, price):
        try:
            wait = WebDriverWait(self.driver, 10)

            # Wait for and enter Quantity
            qty_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@formcontrolname='quantity']"))
            )
            qty_input.clear()
            qty_input.send_keys(str(quantity))

            # Wait for and enter Price
            price_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@formcontrolname='price']"))
            )
            price_input.clear()
            price_input.send_keys(str(price))
            logger.info(f"Entered trade details: Quantity={quantity}, Price={price}")

        except Exception as e:
            logger.info("Error entering trade details: %s", e)
            self.driver.save_screenshot("enter_trade_error.png")
    
    def extract_stock_data(self):
        data = {
            "ltp": "",
            "change": "",
            "low": "",
            "high": "",
            "open": "",
            "day_high": "",
            "day_low": "",
            "avg_price": "",
            "pre_close": "",
            "52w_high": "",
            "52w_low": ""
        }

        try:
            wait = WebDriverWait(self.driver, 10)

            # Get all 'order__form--prodtype' containers
            elements = wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "order__form--prodtype"))
            )

            for el in elements:
                label = el.find_element(By.CLASS_NAME, "order__form--label").text.strip()
                value = ""

                # LTP is not inside a <b> or <span>, it’s a direct text node — extract manually
                if label == "LTP":
                    full_text = el.text.strip()
                    value = full_text.split("\n")[1].strip() if "\n" in full_text else full_text.replace("LTP", "").strip()
                    change_elem = el.find_elements(By.CLASS_NAME, "change-price")
                    data["change"] = change_elem[0].text.strip() if change_elem else ""
                    data["ltp"] = value

                else:
                    # For all others, the value is inside <b>
                    try:
                        value = el.find_element(By.TAG_NAME, "b").text.strip()
                    except:
                        value = ""

                    # Map label to the corresponding key
                    mapping = {
                        "Low": "low",
                        "High": "high",
                        "Open": "open",
                        "D High": "day_high",
                        "D Low": "day_low",
                        "Avg Price": "avg_price",
                        "Pre Close": "pre_close",
                        "52W High": "52w_high",
                        "52W Low": "52w_low"
                    }

                    if label in mapping:
                        data[mapping[label]] = value

        except Exception as e:
            logger.info("Error extracting stock data: %s", e)
            self.driver.save_screenshot("stock_data_error.png")

        return data

    def extract_ltp(self) -> float:
        raw_ltp =  self.extract_stock_data().get("ltp", "").replace(",", "")
        # raw ltp = '723 (2.3)'
        # Extract only the numeric part
        ltp = raw_ltp.split(" ")[0] if raw_ltp else "0"
        return float(ltp)

    def extract_market_depth(self):
        market_depth = {
            "buy": [],   # List of dicts: [{"order": ..., "qty": ..., "price": ...}]
            "sell": []   # List of dicts: [{"price": ..., "qty": ..., "order": ...}]
        }

        try:
            wait = WebDriverWait(self.driver, 10)

            # Get all tables (Top 5 Buy is first, Top 5 Sell is second)
            tables = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.table--data"))
            )

            # --- Extract Buy Side ---
            buy_rows = tables[0].find_elements(By.CSS_SELECTOR, "tbody tr.text-buy")
            for row in buy_rows:
                cols = row.find_elements(By.CLASS_NAME, "text-center")
                if len(cols) == 3:
                    market_depth["buy"].append({
                        "order": cols[0].text.strip(),
                        "qty": cols[1].text.strip(),
                        "price": cols[2].text.strip()
                    })

            # --- Extract Sell Side ---
            sell_rows = tables[1].find_elements(By.CSS_SELECTOR, "tbody tr.text-sell")
            for row in sell_rows:
                cols = row.find_elements(By.CLASS_NAME, "text-center")
                if len(cols) == 3:
                    market_depth["sell"].append({
                        "price": cols[0].text.strip(),
                        "qty": cols[1].text.strip(),
                        "order": cols[2].text.strip()
                    })

        except Exception as e:
            logger.info("Error extracting market depth: %s", e)
            self.driver.save_screenshot("market_depth_error.png")

        return market_depth

    def click_buy_button(self):
        try:
            wait = WebDriverWait(self.driver, 10)

            # Locate the BUY button (with both "btn-primary" and text "BUY")
            buy_button = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, "//button[contains(@class, 'btn-primary') and normalize-space(text())='BUY']"
                ))
            )

            buy_button.click()
            logger.info("BUY button clicked successfully.")

        except Exception as e:
            logger.info("Failed to click BUY button: %s", e)
            self.driver.save_screenshot("buy_button_error.png")

    def click_sell_button(self):
        try:
            sell_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'SELL')]")
            sell_button.click()
            logger.info("Sell button clicked.")
        except Exception as e:
            logger.info("Error clicking sell button: %s", e)
            self.driver.save_screenshot("click_sell_error.png")

    def wait_for_toast(self, timeout=10) -> str:
        try:
            wait = WebDriverWait(self.driver, timeout)
            toast_container = wait.until(EC.presence_of_element_located((By.ID, "toasty")))

            # Wait for any visible toast inside the container
            toast = toast_container.find_element(By.CLASS_NAME, "toast-text")
            title = toast.find_element(By.CLASS_NAME, "toast-title").text
            message = toast.find_element(By.CLASS_NAME, "toast-msg").text

            full_message = f"{title}: {message}"
            print("🔔 Toast:", full_message)
            return full_message

        except TimeoutException:
            print("⏰ Toast message did not appear in time.")
            return "Timeout"

        except Exception as e:
            print(f"❌ Error while parsing toast: {e}")
            return "Error"

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

            logger.info("✅ Navigated to Market Depth")

            return True

        except TimeoutException:
            logger.info("❌ Could not navigate to Market Depth")
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
            logger.info(f"✅ Selected Instrument Type: {instrument_type}")

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
            logger.info(f"✅ Selected Script: {script_name}")

            # Step 4: Wait for market depth table to load
            table = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.market__depth__general-info"))
            )
            logger.info("✅ Market depth table loaded")

            return table.get_attribute("outerHTML")

        except TimeoutException as e:
            logger.info("❌ Failed to load market depth")
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
            logger.info(f"Failed to navigate to place order page: {e}")
            self.driver.save_screenshot("place_order_failed.png")
            return False
