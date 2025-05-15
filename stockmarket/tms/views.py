from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .forms import TMSLoginForm
from .selenium_client import SeleniumTMSClient
import logging
logger = logging.getLogger("tms")

# TEMPORARY session cache (not production-safe)
session_cache = {}

def tms_login_view(request):
    if request.method == "POST":
        form = TMSLoginForm(request.POST)
        if form.is_valid():
            broker = form.cleaned_data['broker_number']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            client = SeleniumTMSClient(broker)
            client.open_login_page()
            captcha_img = client.get_captcha_base64()

            client.fill_credentials(username, password)
            session_cache["client"] = client  # store client for next step

            return render(request, "tms/enter_captcha.html", {
                "captcha_img": captcha_img,
                "broker": broker
            })
    else:
        form = TMSLoginForm()
    return render(request, "tms/login_form.html", {"form": form})



@csrf_exempt
def submit_captcha(request):
    if request.method == "POST":
        captcha_text = request.POST.get("captcha")
        broker = request.POST.get("broker")

        client:SeleniumTMSClient = session_cache.get("client")
        if not client:
            return render(request, "tms/login_form.html", {
                "form": TMSLoginForm(),
                "error": "Session expired. Please try again."
            })

        client.submit_login(captcha_text)
        if client.login_successful():
            dashboard_data = client.scrape_dashboard_stats()
            # html_table = client.get_market_depth_html(instrument_type="EQ", script_name="MEN")
            client.go_to_place_order(script_name='RURU',transaction='Buy')
            client.close()
            return render(request, "tms/login_success.html", dashboard_data)
            # return render(request, "tms/market_depth.html", {"table_html": html_table})


        else:
            # Refresh captcha and retry
            captcha_img = client.get_new_captcha()
            return render(request, "tms/enter_captcha.html", {
                "captcha_img": captcha_img,
                "broker": broker,
                "error": "Login failed. Please try again."
            })
