from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from stockmarket import settings
import pandas as pd
import logging

logger = logging.getLogger('stocks')

class BaseScraper:
    def __init__(self, headless=True, timeout=15, chromedriver_path=settings.CHROMEDRIVER_PATH):
        self.headless = headless
        self.timeout = timeout
        self.chromedriver_path = chromedriver_path
        self.driver = self._init_driver()
        self.records = []

    def _init_driver(self):
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        prefs = {"profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.stylesheets": 2,
                "profile.default_content_setting_values.javascript": 1}
        options.add_experimental_option("prefs", prefs)

        service = Service(self.chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def save_to_csv(self, filename):
        if not self.records:
            print("⚠ No data to save.")
            return
        df = pd.DataFrame(self.records)
        df.to_csv(filename, index=False)
        logger.info(f"📁 Data saved to {filename}")

    def close(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
