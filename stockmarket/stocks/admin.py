from django.contrib import admin
from .models import CompanyProfile, CompanyNews, PriceHistory

admin.site.register(CompanyProfile)
admin.site.register(CompanyNews)
admin.site.register(PriceHistory)
