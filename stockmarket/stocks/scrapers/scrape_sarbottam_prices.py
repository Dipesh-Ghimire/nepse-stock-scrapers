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

# Now you can import your Django models
from stocks.models import PriceHistory, CompanyProfile

def scrape_sarbottam_prices():
    # Path to the chromedriver executable (replace with the correct path on your system)
    chromedriver_path = "/home/dipesh/Desktop/chromedriver-linux64/chromedriver"  # Adjust the path
    
    # Set up the Chrome options (optional for headless mode)
    options = Options()
    # Uncomment the next line to run Chrome in headless mode
    # options.add_argument('--headless')
    
    # Set up the service for ChromeDriver
    service = Service(chromedriver_path)
    
    # Start a new Chrome session
    driver = webdriver.Chrome(service=service, options=options)
    
    # Open the page
    driver.get("https://www.sharesansar.com/company/sarbtm")
    
    # Wait for the page to fully load
    time.sleep(3)  # You may adjust the sleep time as needed

    # Find the "Price History" tab and click it
    price_history_tab = driver.find_element(By.ID, "btn_cpricehistory")
    price_history_tab.click()
    
    # Wait for the content to load after the tab is clicked
    time.sleep(3)  # Wait for the tab content to load

    # Find the table containing the price history data
    price_history_table = driver.find_element(By.ID, "myTableCPriceHistory")
    
    # Find all rows in the table
    rows = price_history_table.find_elements(By.TAG_NAME, "tr")
    
    # Get the CompanyProfile object for Sarbottam Cement
    company = CompanyProfile.objects.get(symbol="SARBTM")

    # Extract the data from each row
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        
        # Check if the row contains columns
        if len(cols) > 0:
            date = cols[1].text.strip()
            open_price = cols[2].text.strip()
            high_price = cols[3].text.strip()
            low_price = cols[4].text.strip()
            ltp = cols[5].text.strip()  # Close price is same as LTP (Last Traded Price)
            percentage_change = cols[6].text.strip()
            qty = cols[7].text.strip()
            turnover = cols[8].text.strip()

            # Format the date to match Django's date format
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()

            # Save the price history data into the database
            price_history = PriceHistory(
                company=company,
                date=date_obj,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=ltp,  # Close price is same as LTP (Last Traded Price)
            )
            price_history.save()
            print(f"Saved data for {date} - Open: {open_price}, High: {high_price}, Low: {low_price}, LTP: {ltp}")

    # Quit the driver after scraping
    driver.quit()
