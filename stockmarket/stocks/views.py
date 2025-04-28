import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.shortcuts import render
from django.http import JsonResponse

from .models import CompanyNews, CompanyProfile, PriceHistory
from .scrapers.scrape_prices import scrape_company_price_history

from statsmodels.tsa.arima.model import ARIMA
from django.http import JsonResponse
import pandas as pd

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
        model = ARIMA(df['close_price'], order=(5, 1, 0))  # Example: ARIMA(5,1,0)
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
    prices = PriceHistory.objects.select_related('company').order_by('-date')
    return render(request, 'stocks/price_history_list.html', {'prices': prices})

def company_list(request):
    companies = CompanyProfile.objects.all()
    return render(request, 'stocks/company_list.html', {'companies': companies})

def company_news_list(request):
    news = CompanyNews.objects.all()
    return render(request, 'stocks/company_news_list.html', {'news': news})

def scrape_company_prices(request, id):
    try:
        company = CompanyProfile.objects.get(id=id)
        scrape_company_price_history(company.symbol)  # Use the generalized scraper
        return JsonResponse({'message': f"Successfully scraped prices for {company.name}."})
    except CompanyProfile.DoesNotExist:
        return JsonResponse({'message': 'Company not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)