from django import forms

class TMSLoginForm(forms.Form):
    broker_number = forms.IntegerField(label="Broker Number", min_value=1)
    username = forms.CharField(label="Username", required=True)
    password = forms.CharField(widget=forms.PasswordInput(), label="Password", required=True)

    script_name = forms.CharField(label="Script Name", max_length=10)
    
    TRANSACTION_CHOICES = [
        ('Buy', 'BUY'),
        ('Sell', 'SELL'),
    ]
    transaction_type = forms.ChoiceField(label="Transaction", choices=TRANSACTION_CHOICES)

    price = forms.DecimalField(label="Target Price", max_digits=10, decimal_places=1, required=True, min_value=1)
    quantity = forms.IntegerField(label="Quantity" , min_value=10, required=True)
    price_threshold = forms.DecimalField(label="Price Threshold", max_digits=10, decimal_places=1, required=False, min_value=1)