from django.urls import path
from . import views

urlpatterns = [
    # Other URL patterns...
    path('tms/', views.tms_login_view, name='tms_login'),
    path('submit-captcha/', views.submit_captcha, name='submit_captcha'),
]
