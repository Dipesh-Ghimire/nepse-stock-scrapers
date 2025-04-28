from django.db import models

class CompanyProfile(models.Model):
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=50)
    sector = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    listed_date = models.DateField(null=True, blank=True)
    paidup_capital = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    listed_shares = models.BigIntegerField(null=True, blank=True)
    market_capitalization = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CompanyNews(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE)
    news_title = models.CharField(max_length=255)
    news_date = models.DateField()
    news_image = models.URLField(null=True, blank=True)
    news_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.news_title

class PriceHistory(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.symbol} - {self.date}"
