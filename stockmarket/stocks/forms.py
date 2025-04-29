from django import forms
from .models import CompanyProfile, CompanyNews, PriceHistory

# Form for creating or updating CompanyProfile
class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['name', 'symbol', 'sector', 'address', 'website', 'listed_date', 'paidup_capital', 'listed_shares', 'market_capitalization', 'description']

class CompanyNewsForm(forms.ModelForm):
    class Meta:
        model = CompanyNews
        fields = ['company', 'news_title', 'news_date', 'news_image', 'news_body']