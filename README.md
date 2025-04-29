## Stock Market Web Application Project Flow

Here’s a video showcasing the project flow:

![Project Flow](https://youtu.be/CIapr-ea8QY](https://www.youtube.com/watch?v=CIapr-ea8QY&ab_channel=Dipesh)


This project is a **Django-based web application** that allows users to:

- Manage company profiles
- View and add latest company news
- View stock price history (Sharesansar)
- Scrape the latest stock prices (using Selenium)
- Predict future stock prices using time series forecasting (ARIMA model)

---

## 🚀 Features

- CRUD operations for **Company Profiles**, **Company News**, and **Price History**.
- Web scraping for real-time stock prices (customized per company).
- Future price prediction using **ARIMA** model.
- Responsive frontend designed with **Bootstrap 5**.
- RESTful-like URL patterns for smooth navigation.

---

## 🛠 Project Setup Instructions

Follow these steps to set up the project locally:

### 1. Clone the Repository

```bash
git clone https://github.com/Dipesh-Ghimire/python_task.git
cd python_task
```
---

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
```

---

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

### 4. Apply Migrations

```bash
python stockmarket/manage.py migrate
```
---

### 5. Run the Development Server

```bash
python stockmarket/manage.py runserver
```


---


