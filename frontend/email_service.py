import smtplib
import os
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
FROM_NAME = os.getenv("FROM_NAME", "Billing System")
shop_name = os.getenv("shop_name", "Your Shop")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Store email_logs.csv in the specified folder
DATA_FOLDER = r"D:\Projects\Customer_Due_Tracker_System\backend\data"
os.makedirs(DATA_FOLDER, exist_ok=True)  # Ensure folder exists
EMAIL_LOG_FILE = os.path.join(DATA_FOLDER, 'email_logs.csv')


def log_email(customer_id, customer_email, subject, status):
    """Append email log to CSV and also print to console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Log to console
    print(f"[{timestamp}] CustomerID: {customer_id}, Email: {customer_email}, Subject: {subject}, Status: {status}")

    # Append to CSV
    file_exists = os.path.exists(EMAIL_LOG_FILE)
    with open(EMAIL_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp','customer_id','customer_email','subject','status'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'timestamp': timestamp,
            'customer_id': customer_id,
            'customer_email': customer_email,
            'subject': subject,
            'status': status
        })


def send_email(to_email, subject, body, customer_id=''):
    """Send an email and log to console & CSV."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{FROM_NAME} <{EMAIL_ADDRESS}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        log_email(customer_id, to_email, subject, 'Sent')

    except Exception as e:
        log_email(customer_id, to_email, subject, f'Failed: {e}')


def send_daily_due_email(customers):
    """Send daily due reminder emails to all customers with outstanding dues."""
    for cust in customers:
        if cust.get('due', 0) > 0 and cust.get('email'):
            subject = f"{shop_name} - Daily Due Reminder"
            body = f"""Hello {cust['name']},

We wanted to remind you that your current outstanding due with {shop_name} is ₹{cust['due']:.2f}.

If you have already made the payment, please ignore this message.
If this reminder was sent in error or you believe your account is up-to-date, please contact us immediately so we can assist you.

We appreciate your prompt attention to this matter.

Thank you,  
— {shop_name} Team
"""
            send_email(cust['email'], subject, body, customer_id=cust.get('id', ''))


# NEW FUNCTIONS FOR CREDENTIAL MANAGEMENT
def send_welcome_email(customer_data):
    """Send welcome email with login credentials to new customers."""
    if not customer_data.get('email'):
        return False

    subject = f"Welcome to {shop_name} - Your Account Details"
    body = f"""Dear {customer_data['name']},

Welcome to {shop_name}! Your account has been successfully created.

Here are your login credentials:
Username: {customer_data['username']}
Password: {customer_data['password']}

Please log in to our system using these credentials. 
We recommend changing your password after first login.

If you have any questions, please don't hesitate to contact us.

Thank you,
— {shop_name} Team
"""
    send_email(
        customer_data['email'],
        subject,
        body,
        customer_id=customer_data.get('id', '')
    )
    return True


def send_credentials_reset_email(customer_data):
    """Send email when credentials are reset by admin."""
    if not customer_data.get('email'):
        return False

    subject = f"{shop_name} - Your Account Credentials Have Been Updated"
    body = f"""Dear {customer_data['name']},

Your account credentials have been updated by our admin team.

Here are your new login details:
Username: {customer_data['username']}
Password: {customer_data['password']}

Please log in using these new credentials. 
For security reasons, we recommend changing your password after login.

If you didn't request this change, please contact us immediately.

Thank you,
— {shop_name} Team
"""
    send_email(
        customer_data['email'],
        subject,
        body,
        customer_id=customer_data.get('id', '')
    )
    return True
