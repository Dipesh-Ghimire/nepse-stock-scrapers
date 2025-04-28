import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.shortcuts import render
from django.http import JsonResponse

from .scrapers.scrape_sarbottam_prices import scrape_sarbottam_prices
from .models import PriceHistory

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.http import JsonResponse
from .models import PriceHistory

def fetch_price_history():
    # Fetch the last 20 price history records from the database
    price_data = PriceHistory.objects.all().order_by('-date')[:20]
    
    # Prepare the data for ARIMA (date and close_price)
    data = pd.DataFrame(list(price_data.values('date', 'close_price')))
    data['date'] = pd.to_datetime(data['date'])
    data = data.set_index('date')
    
    # Sort the data by date and set frequency to daily (asfreq)
    data = data.sort_index()
    data = data.asfreq('D')  # This ensures a daily frequency for the time series
    
    # Ensure close_price is numeric, forcing errors to NaN
    data['close_price'] = pd.to_numeric(data['close_price'], errors='coerce')
    
    # Drop rows with NaN values (if any) in 'close_price'
    data = data.dropna(subset=['close_price'])
    
    return data

def predict_future_prices(request):
    # Step 1: Fetch historical data
    data = fetch_price_history()
    
    if len(data) < 2:  # Ensure we have enough data for ARIMA
        return JsonResponse({'message': 'Not enough data for prediction. Need at least 2 data points.'}, status=400)
    
    # Step 2: Fit an ARIMA model
    try:
        # Log the data we're passing to ARIMA
        print("Using the following data for ARIMA model:")
        print(data.head())  # Log the first few rows of the data
        
        # Fit the ARIMA model
        model = ARIMA(data['close_price'], order=(5, 1, 0))
        model_fit = model.fit()
        
        # Log the model summary
        print("ARIMA Model Summary:")
        print(model_fit.summary())

        # Step 3: Forecast the next 5 days
        forecast = model_fit.forecast(steps=5)
        
        # Prepare forecast dates (next 5 days)
        future_dates = pd.date_range(start=data.index[-1] + pd.Timedelta(days=1), periods=5, freq='D')
        
        # Prepare forecasted results to return
        forecast_result = [{"date": future_dates[i].strftime('%Y-%m-%d'), "predicted_close_price": forecast[i]} for i in range(5)]
        
        return JsonResponse({'predictions': forecast_result})
    
    except Exception as e:
        # Log any exceptions
        print(f"Error occurred: {str(e)}")
        return JsonResponse({'message': f'Error occurred while forecasting: {str(e)}'}, status=500)

def scrape_button(request):
    return render(request, 'stocks/scrape_button.html')

def scrape_prices(request):
    try:
        # Trigger scraping function
        scrape_sarbottam_prices()

        # Return a success message after scraping
        return JsonResponse({'message': 'Prices scraped successfully!'})
    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
