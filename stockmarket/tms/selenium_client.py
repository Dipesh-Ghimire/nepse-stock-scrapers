from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

