from django import forms

class TMSLoginForm(forms.Form):
    broker_number = forms.IntegerField(label="Broker Number")
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput(), label="Password")
