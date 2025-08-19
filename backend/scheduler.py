import threading
import time
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from .notifications.email_service import send_daily_due_email

# Load env variables
load_dotenv()
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
CUSTOMERS_CSV = os.path.join(DATA_PATH, 'customers.csv')
DAILY_HOUR = int(os.getenv("DAILY_EMAIL_HOUR", 9))
DAILY_MINUTE = int(os.getenv("DAILY_EMAIL_MINUTE", 0))


def load_customers():
    if os.path.exists(CUSTOMERS_CSV):
        df = pd.read_csv(CUSTOMERS_CSV)
        df['due'] = pd.to_numeric(df.get('due', 0), errors='coerce')
        return df.to_dict(orient='records')
    return []


def daily_email_scheduler():
    """
    Runs indefinitely and sends due emails daily at the specified hour and minute.
    """
    while True:
        now = datetime.now()
        if now.hour == DAILY_HOUR and now.minute == DAILY_MINUTE:
            print("[INFO] Sending daily due emails...")
            customers = load_customers()
            send_daily_due_email(customers)
            # Sleep 61 seconds to prevent sending multiple times within the same minute
            time.sleep(61)
        else:
            time.sleep(20)  # check every 20 seconds


def start_scheduler():
    thread = threading.Thread(target=daily_email_scheduler, daemon=True)
    thread.start()
