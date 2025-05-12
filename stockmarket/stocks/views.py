import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import HttpResponseRedirect

from .scrapers import merolagani_scraper
from .scrapers import sharesansar_scraper
from .scrapers.nepstock_scraper import scrape_company_price_history_nepstock, scrape_company_floorsheet_nepstock
from .utility import save_price_history_to_db_ml, save_price_history_to_db, save_price_history_to_db_ss, store_floorsheet_to_db_ss, store_floorsheet_to_db_ml, store_news_to_db_ml
from .forms import CompanyNewsForm, CompanyProfileForm

from .models import CompanyNews, CompanyProfile, PriceHistory, FloorSheet

from statsmodels.tsa.arima.model import ARIMA

import logging
logger = logging.getLogger('stocks')

def fetch_price_history(company):
    # Fetch PriceHistory records for this specific company
    qs = PriceHistory.objects.filter(company=company).order_by('date')

    # Convert QuerySet to DataFrame
    data = pd.DataFrame.from_records(qs.values('date', 'close_price'))
    data.set_index('date', inplace=True)
    
    return data


def predict_future_prices(request, id):
    try:
        # Fetch company and price history based on the company ID
        company = CompanyProfile.objects.get(id=id)
        prices = PriceHistory.objects.filter(company=company).order_by('date')

        # If there is no price history available for the company
        if not prices.exists():
            return JsonResponse({'message': 'No price history available for prediction.'}, status=400)

        # Convert price history into a Pandas DataFrame
        df = pd.DataFrame(list(prices.values('date', 'close_price')))
        
        # Ensure the date column is set as the index and convert it to datetime
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Set a daily frequency and forward fill missing data
        df = df.asfreq('D', method='ffill')

        # Convert close_price to numeric and drop any invalid rows (NaN after conversion)
        df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
        df = df.dropna(subset=['close_price'])  # Drop rows where 'close_price' is NaN

        # If not enough data to make a prediction, return an error message
        if len(df) < 10:
            return JsonResponse({'message': 'Not enough data to make a prediction. Need at least 10 data points.'}, status=400)

        # Fit the ARIMA model (you can adjust the order depending on your data)
        model = ARIMA(df['close_price'], order=(20, 1, 0))  # Example: ARIMA(5,1,0)
        model_fit = model.fit()

        # Forecast the next 5 days
        forecast = model_fit.forecast(steps=5)

        # Generate future dates for the forecast
        last_date = df.index[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=5, freq='D')

        # Prepare the forecast result
        forecast_result = [
            {"date": future_dates[i].strftime('%Y-%m-%d'), "predicted_close_price": round(float(forecast.iloc[i]), 2)}
            for i in range(5)
        ]

        # Return the result as a JSON response
        return JsonResponse({'predictions': forecast_result})

    except Exception as e:
        # Handle any unexpected exceptions
        return JsonResponse({'message': f'Error occurred while forecasting: {str(e)}'}, status=500)

def home(request):
    return render(request, 'stocks/home.html')

def company_detail(request, id):
    company = CompanyProfile.objects.get(id=id)
    return render(request, 'stocks/company_detail.html', {'company': company})

def company_news(request, id):
    company = CompanyProfile.objects.get(id=id)
    company_news = CompanyNews.objects.filter(company=company)
    return render(request, 'stocks/company_news.html', {'company': company, 'company_news': company_news})

def price_history(request, id):
    company = CompanyProfile.objects.get(id=id)
    price_history = PriceHistory.objects.filter(company=company)
    return render(request, 'stocks/price_history.html', {'company': company, 'price_history': price_history})

def price_history_list(request):
    price_list = PriceHistory.objects.select_related('company').order_by('-date')
    paginator = Paginator(price_list, 25)  # Show 25 records per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'stocks/price_history_list.html', {'page_obj': page_obj,})

def company_list(request):
    companies = CompanyProfile.objects.all()
    return render(request, 'stocks/company_list.html', {'companies': companies})

def company_news_list(request):
    news = CompanyNews.objects.all()
    return render(request, 'stocks/company_news_list.html', {'news': news})

def scrape_sharesansar_pricehistory(request, id):
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        scraper = sharesansar_scraper.SharesansarPriceScraper(symbol=symbol, headless=True)
        data = scraper.fetch_price_history()
        logger.info(f"Scraped {len(data)} records for {symbol} from Sharesansar")

        save_price_history_to_db_ss(symbol, data)

        return JsonResponse({'message': f"Successfully scraped prices for {company.name}."})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'message': 'Company not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
    
def scrape_nepstock_pricehistory(request, id):
    """
    Scrape price history for a specific company using the NepalStock scraper.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        # Step 1: Scrape
        price_history_data = scrape_company_price_history_nepstock(symbol, max_pages=8, output_csv=False)
        logger.info(f"Scraped {len(price_history_data)} records for {symbol} from NepalStock")

        # Step 2: Save to DB using unified function
        save_price_history_to_db(symbol, price_history_data)
        return JsonResponse({
            "message": f"Scraped and saved {len(price_history_data)} records for {symbol}",
            'records_scraped': len(price_history_data)
        })
    except CompanyProfile.DoesNotExist:
        return JsonResponse({"error": f"Company with ID {id} not found."}, status=404)
    except Exception as e:
        logger.exception("Error scraping from NepalStock")
        return JsonResponse({'error': str(e)}, status=500)

def scrpae_merolagani_pricehistory(request, id):
    """
    Scrape price history for a specific company using the Merolagani scraper.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        scraper = merolagani_scraper.MerolaganiScraper(symbol=symbol, headless=True)
        data = scraper.fetch_price_history(max_records=150)
        logger.info(f"Scraped {len(data)} records for {symbol} from Merolagani")

        # Save using the same unified function
        save_price_history_to_db_ml(symbol, data)

        return JsonResponse({
            "message": f"Scraped and saved {len(data)} records for {symbol}",
            "records_saved": len(data)
        })
    except CompanyProfile.DoesNotExist:
        return JsonResponse({"error": f"Company with ID {id} not found."}, status=404)
    except Exception as e:
        logger.exception("Error scraping from Merolagani")
        return JsonResponse({"error": str(e)}, status=500)

def company_create(request):
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyProfileForm()
    return render(request, 'stocks/company_form.html', {'form': form})

def add_company_news(request):
    if request.method == 'POST':
        form = CompanyNewsForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_news_list')  # Make sure you have this URL name
    else:
        form = CompanyNewsForm()
    return render(request, 'stocks/company_news_form.html', {'form': form})

def company_news_detail(request, news_id):
    news_article = CompanyNews.objects.get(id=news_id)
    return render(request, 'stocks/company_news_detail.html', {'article': news_article})
def delete_all_price_records(request):
    if request.method == 'POST':
        deleted_count, _ = PriceHistory.objects.all().delete()
        return redirect('price_history_list')  # Redirect to the price history list after deletion
    return render(request, 'stocks/delete_all_price_records.html')

def list_floorsheet(request, id):
    """
    List the floorsheet for a specific company.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        floorsheet = FloorSheet.objects.filter(company=company).order_by('-date')
        return render(request, 'stocks/floorsheet_list.html', {'company': company, 'floorsheet': floorsheet})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'error': 'Company not found.'}, status=404)
    except Exception as e:
        logger.exception("Error fetching floorsheet")
        return JsonResponse({'error': str(e)}, status=500)

def scrape_floorsheet_ss(request, id):
    """
    Scrape the floorsheet for a specific company using the Sharesansar scraper.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        scraper = sharesansar_scraper.SharesansarFloorsheetScraper(symbol=symbol, headless=True)
        floorsheet_data = scraper.fetch_floorsheet()
        logger.info(f"Scraped {len(floorsheet_data)} floorsheet for {symbol} from Sharesansar")

        # Save to DB
        store_floorsheet_to_db_ss(symbol, floorsheet_data)

        return JsonResponse({'message': f"Successfully scraped floorsheet for {company.name}."})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'message': 'Company not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
def scrape_floorsheet_ml(request, id):
    """
    Scrape the floorsheet for a specific company using the Sharesansar scraper.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        logger.info(f"Scraping floorsheet for {symbol} from Merolagani")
        scraper = merolagani_scraper.MerolaganiFloorsheetScraper(headless=True)
        floorsheet_data = scraper.run_scraper(symbol=symbol)
        logger.info(f"Scraped {len(floorsheet_data)} floorsheet for {symbol} from Merolagani")
        # Save to DB
        store_floorsheet_to_db_ml(symbol, floorsheet_data)

        return JsonResponse({'message': f"Successfully scraped floorsheet for {company.name}."})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'message': 'Company not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
    
def scrape_floorsheet_nepstock(request, id):
    try:
        company = CompanyProfile.objects.get(id=id)
        symbol = company.symbol

        # Step 1: Scrape
        floorsheet_data = scrape_company_floorsheet_nepstock(symbol, headless=False)
        logger.info(f"Scraped {len(floorsheet_data)} records for {symbol} from NepalStock")

        # Step 2: Save to DB using unified function
        print(floorsheet_data)
        return JsonResponse({
            "message": f"Scraped and saved {len(floorsheet_data)} records for {symbol}",
            'records_scraped': len(floorsheet_data)
        })
    except CompanyProfile.DoesNotExist:
        return JsonResponse({"error": f"Company with ID {id} not found."}, status=404)
    except Exception as e:
        logger.exception("Error scraping from NepalStock")
        return JsonResponse({'error': str(e)}, status=500)

def scrape_news_ml(request):
    scraper = merolagani_scraper.MerolaganiNewsScraper(headless=False, max_records=8)
    records = scraper.fetch_news()
    record_with_body = scraper._extract_news_body(records=records)
    store_news_to_db_ml(news_data=record_with_body)
    scraper.close()
    return render(request, 'stocks/company_news_list.html', {'news': CompanyNews.objects.all()})

def empty_floorsheet(request, id):
    """
    Empty the floorsheet for a specific company.
    """
    try:
        company = CompanyProfile.objects.get(id=id)
        if request.method == 'POST':
            FloorSheet.objects.filter(company=company).delete()
            return redirect('floorsheet_list', id=id)
        return render(request, 'stocks/delete_floorsheet.html', {'company': company})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'error': 'Company not found.'}, status=404)
    except Exception as e:
        logger.exception("Error emptying floorsheet")
        return JsonResponse({'error': str(e)}, status=500)