import os
import json
import razorpay

# Path to Razorpay keys JSON file
KEYS_FILE = os.path.join(os.path.dirname(__file__), "data", "razorpay_keys.json")


def save_keys(key_id, key_secret, mode="test"):
    """
    Save Razorpay credentials to JSON file.
    mode: 'test' or 'live'
    """
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    data = {
        "key_id": key_id,
        "key_secret": key_secret,
        "mode": mode  # save mode for reference
    }
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f)
    return True


def read_keys():
    """Read Razorpay keys from JSON file."""
    if not os.path.exists(KEYS_FILE):
        return None, None, None
    try:
        with open(KEYS_FILE, "r") as f:
            data = json.load(f)
            return data.get("key_id"), data.get("key_secret"), data.get("mode")
    except Exception:
        return None, None, None


def get_client():
    """Return a Razorpay client using saved keys."""
    key_id, key_secret, mode = read_keys()
    if not key_id or not key_secret:
        raise Exception("Razorpay keys not set. Please save them in the admin panel.")
    client = razorpay.Client(auth=(key_id, key_secret))
    if mode == "test":
        client.set_app_details({"title": "CustomerDueTracker", "version": "1.0"})
    return client


def create_upi_order(amount, upi_id, currency="INR"):
    """
    Create a UPI collect order.
    amount: float (INR)
    upi_id: string (customer UPI)
    currency: default INR
    """
    client = get_client()
    try:
        order = client.order.create({
            "amount": int(amount * 100),  # convert to paise
            "currency": currency,
            "payment_capture": 1,
            "notes": {"upi_id": upi_id}
        })
        return order
    except razorpay.errors.BadRequestError as e:
        return {"error": f"Bad request: {e}"}
    except razorpay.errors.ServerError as e:
        return {"error": f"Server error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def check_payment_status(payment_id):
    """Check payment status by ID."""
    client = get_client()
    try:
        payment = client.payment.fetch(payment_id)
        return payment.get("status")  # "captured", "failed", etc.
    except razorpay.errors.BadRequestError as e:
        return f"Bad request: {e}"
    except razorpay.errors.ServerError as e:
        return f"Server error: {e}"
    except Exception as e:
        return f"error: {e}"
