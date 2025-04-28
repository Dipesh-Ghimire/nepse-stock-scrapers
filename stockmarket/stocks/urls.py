from django.urls import path
from . import views

urlpatterns = [
    # Other URL patterns...
    path('scrape/', views.scrape_button, name='scrape_button'),
    path('scrape_prices/', views.scrape_prices, name='scrape_prices'),
    path('predict_prices/', views.predict_future_prices, name='predict_future_prices'),  
]
