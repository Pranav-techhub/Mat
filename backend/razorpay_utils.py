import os
import json
import razorpay
from datetime import datetime

# Path to Razorpay keys JSON file
KEYS_FILE = os.path.join(os.path.dirname(__file__), "data", "razorpay_keys.json")


def save_keys(key_id, key_secret):
    """Save Razorpay credentials to JSON file."""
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    with open(KEYS_FILE, "w") as f:
        json.dump({"key_id": key_id, "key_secret": key_secret}, f)
    return True


def read_keys():
    """Read Razorpay keys from JSON file."""
    if not os.path.exists(KEYS_FILE):
        return None, None
    try:
        with open(KEYS_FILE, "r") as f:
            data = json.load(f)
            return data.get("key_id"), data.get("key_secret")
    except Exception:
        return None, None


def get_client():
    """Return a Razorpay client using saved keys."""
    key_id, key_secret = read_keys()
    if not key_id or not key_secret:
        raise Exception("Razorpay keys not set. Please save them in the admin panel.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_upi_order(amount, upi_id):
    """Create UPI collect order."""
    client = get_client()
    order = client.order.create({
        "amount": int(amount * 100),  # paise
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"upi_id": upi_id}
    })
    return order


def check_payment_status(payment_id):
    """Check payment status by ID."""
    client = get_client()
    try:
        payment = client.payment.fetch(payment_id)
        return payment.get("status")
    except Exception as e:
        return f"error: {e}"
