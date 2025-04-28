import os
import django
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time

# Set up the Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockmarket.settings")
django.setup()

# Import your Django models
from stocks.models import PriceHistory, CompanyProfile

def scrape_company_price_history(symbol):
    """
    Scrapes and saves price history for the given company's symbol.
    Example: 'USHL', 'NABIL', 'NLIC'
    """
    # Path to the chromedriver executable
    chromedriver_path = "/home/dipesh/Desktop/chromedriver-linux64/chromedriver"  # Adjust this

    # Set up Chrome options (optional: headless mode)
    options = Options()
    # options.add_argument('--headless')

    # Set up ChromeDriver service
    service = Service(chromedriver_path)

    # Start a Chrome session
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open the company's page
        url = f"https://www.sharesansar.com/company/{symbol}"
        driver.get(url)

        # Wait for page to load
        time.sleep(3)

        # Click the "Price History" tab
        price_history_tab = driver.find_element(By.ID, "btn_cpricehistory")
        price_history_tab.click()

        # Wait for tab content to load
        time.sleep(3)

        # Find the price history table
        price_history_table = driver.find_element(By.ID, "myTableCPriceHistory")
        rows = price_history_table.find_elements(By.TAG_NAME, "tr")

        # Fetch the company object
        try:
            company = CompanyProfile.objects.get(symbol=symbol)
        except CompanyProfile.DoesNotExist:
            print(f"Company with symbol '{symbol}' not found in database.")
            return

        # Extract and save data
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if cols:
                try:
                    date = cols[1].text.strip()
                    open_price = cols[2].text.strip()
                    high_price = cols[3].text.strip()
                    low_price = cols[4].text.strip()
                    close_price = cols[5].text.strip()

                    # Parse date
                    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

                    # Avoid duplicate entries (optional but good practice)
                    if not PriceHistory.objects.filter(company=company, date=date_obj).exists():
                        price_history = PriceHistory(
                            company=company,
                            date=date_obj,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                        )
                        price_history.save()
                        print(f"Saved: {company.symbol} - {date}")
                    else:
                        print(f"Already exists: {company.symbol} - {date}")

                except Exception as e:
                    print(f"Error processing row: {e}")
    except Exception as e:
        print(f"Error scraping {symbol}: {e}")
    finally:
        # Quit the browser
        driver.quit()

# Example usage
if __name__ == "__main__":
    scrape_company_price_history('USHL')
