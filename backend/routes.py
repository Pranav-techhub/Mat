from flask import Blueprint, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Create the Blueprint instance
routes = Blueprint('api_routes', __name__)
CORS(routes)

# Import services
from backend.services import (
    get_all_customers, add_customer, update_due,
    record_partial_payment, delete_customer, delete_all_customers,
    login_user, get_recent_activity, user_pay_due,
    user_delete_account, get_user_transactions,
    reset_credentials  # All required imports
)
from backend.notifications.email_service import send_email, shop_name
from backend.razorpay_utils import save_keys, create_upi_order, check_payment_status
# ============== AUTHENTICATION ROUTES ==============
@routes.route("/user/login", methods=["POST"])
def api_login_user():
    """Unified login endpoint for both customers and legacy users"""
    data = request.json
    success = login_user(data.get("username"), data.get("password"))
    return jsonify({
        "success": success,
        "message": "Login successful" if success else "Invalid credentials"
    })

# ============== ADMIN ROUTES ==============
@routes.route("/admin/customers", methods=["GET"])
def api_get_customers():
    active_only = request.args.get("active_only", "false").lower() == "true"
    return jsonify(get_all_customers(active_only=active_only))

@routes.route("/admin/customer/add", methods=["POST"])
def api_add_customer():
    data = request.json
    cust = add_customer(
        name=data.get("name"),
        phone=data.get("phone"),
        address=data.get("address"),
        due=data.get("due"),
        email=data.get("email", "")
    )
    
    # Send welcome email with credentials
    if cust.get('email'):
        try:
            send_email(
                cust['email'],
                f"Welcome to {shop_name}!",
                f"""Hello {cust['name']},
Your account has been created.

🔐 Login Credentials:
Username: {cust['username']}
Password: {cust['password']}

💰 Current Due: ₹{cust['due']:.2f}

Please change your password after first login.
"""
            )
        except Exception as e:
            print(f"Failed to send welcome email: {e}")

    return jsonify(cust)

@routes.route("/admin/credentials/reset", methods=["POST"])
def api_reset_credentials():
    """Endpoint for admin to reset customer credentials"""
    data = request.json
    result = reset_credentials(
        customer_id=data.get("customer_id"),
        new_username=data.get("new_username"),
        new_password=data.get("new_password")
    )
    
    if not result:
        return jsonify({"error": "Customer not found"}), 404
    
    # Notify customer of credential change
    if result.get('email'):
        try:
            send_email(
                result['email'],
                f"{shop_name} - Account Credentials Updated",
                f"""Hello {result['name']},
Your login credentials have been updated:

Username: {result['username']}
Password: {result['password']}

Please change your password after logging in.
"""
            )
        except Exception as e:
            print(f"Failed to send credentials email: {e}")

    return jsonify(result)

# ----------------- NEW RAZORPAY ENDPOINTS -----------------


@routes.route("/admin/save_keys", methods=["POST"])
def admin_save_keys():
    try:
        data = request.json
        key_id = data.get("key_id")
        key_secret = data.get("key_secret")

        if not key_id or not key_secret:
            return jsonify({"error": "Missing credentials"}), 400

        save_keys(key_id, key_secret)
        return jsonify({"message": "Keys saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/customer/pay", methods=["POST"])
def customer_pay():
    data = request.json
    upi_id = data.get("upi_id")
    amount = data.get("amount")
    if not upi_id or not amount:
        return jsonify({"error": "Missing upi_id or amount"}), 400
    try:
        order = create_upi_order(amount, upi_id)
        return jsonify(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/payment/status/<payment_id>", methods=["GET"])
def payment_status(payment_id):
    status = check_payment_status(payment_id)
    return jsonify({"status": status})

@routes.route("/admin/customer/update_due", methods=["POST"])
def api_update_due():
    data = request.json
    cust = update_due(data.get("id"), data.get("new_due"))
    if not cust:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(cust)

@routes.route("/admin/customer/delete", methods=["POST"])
def api_delete_customer():
    data = request.json
    cust = delete_customer(data.get("id"))
    if not cust:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(cust)

@routes.route("/admin/customer/delete_all", methods=["POST"])
def api_delete_all():
    delete_all_customers()
    return jsonify({"status": "all_deleted"})

@routes.route("/admin/recent_activity", methods=["GET"])
def api_recent_activity():
    return jsonify(get_recent_activity(limit=10))

@routes.route("/admin/user_transactions", methods=["GET"])
def api_user_transactions():
    return jsonify(get_user_transactions(limit=10))

# ============== CUSTOMER USER ROUTES ==============
@routes.route("/user/due/pay", methods=["POST"])
def api_user_pay_due():
    data = request.json
    cust = user_pay_due(
        username=data.get("username"),
        customer_id=data.get("customer_id"),
        amount=data.get("amount")
    )
    if not cust:
        return jsonify({"error": "Payment failed"}), 400
    return jsonify(cust)

@routes.route("/user/account/delete", methods=["POST"])
def api_user_delete_account():
    data = request.json
    cust = user_delete_account(
        username=data.get("username"),
        customer_id=data.get("customer_id")
    )
    if not cust:
        return jsonify({"error": "Cannot delete account"}), 400
    return jsonify(cust)