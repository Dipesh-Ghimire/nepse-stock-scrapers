from django.urls import path
from . import views

urlpatterns = [
    # Other URL patterns...
    path('', views.company_list, name='company_list'),
    path('predict-future-prices/<int:id>/', views.predict_future_prices, name='predict_future_prices'),
    
    path('company/<int:id>/', views.company_detail, name='company_detail'),
    path('company/<int:id>/news/', views.company_news, name='company_news'),
    path('companies/create/', views.company_create, name='company_create'),

    path('company/<int:id>/price-history/', views.price_history, name='price_history'),
    path('news/', views.company_news_list, name='company_news_list'),
    path('news/add/', views.add_company_news, name='add_company_news'),
    path('news/<int:news_id>/', views.company_news_detail, name='company_news_detail'),

    path('prices/', views.price_history_list, name='price_history_list'),

    path('scrape-company/<int:id>/', views.scrape_company_prices, name='scrape_company_prices'),
]
