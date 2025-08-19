# backend/services.py
import os
import pandas as pd
import secrets
import string
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
CUSTOMERS_CSV = os.path.join(DATA_PATH, "customers.csv")
ADDED_CSV = os.path.join(DATA_PATH, "added_customers.csv")
UPDATED_CSV = os.path.join(DATA_PATH, "updated_customers.csv")
PARTIAL_CSV = os.path.join(DATA_PATH, "partial_customers.csv")
DELETED_CSV = os.path.join(DATA_PATH, "deleted_customers.csv")
DUES_CSV = os.path.join(DATA_PATH, "dues.csv")
USERS_CSV = os.path.join(DATA_PATH, "users.csv")  # Existing user login
SIGNUP_CSV = os.path.join(DATA_PATH, "signup.csv")  # For new user signup
SIGNIN_CSV = os.path.join(DATA_PATH, "signin.csv")  # User login
USER_PAYMENT_CSV = os.path.join(DATA_PATH, "user_payment_updated.csv")
USER_DELETED_CSV = os.path.join(DATA_PATH, "user_account_deleted.csv")
SIGNIN_LOGS_CSV = os.path.join(DATA_PATH, "signin_logs.csv")  # NEW for login tracking

os.makedirs(DATA_PATH, exist_ok=True)

# ---------------- CSV Helpers ----------------
def _load_csv(file, cols=None):
    return pd.read_csv(file) if os.path.exists(file) else pd.DataFrame(columns=cols or [])

def _append_csv(file, row):
    pd.DataFrame([row]).to_csv(file, mode='a', header=not os.path.exists(file), index=False)

def _save_csv(df, file):
    df.to_csv(file, index=False)

def _generate_credentials():
    """Generate random username and password"""
    username = f"user_{secrets.token_hex(3)}"  # e.g. user_a1b2c3
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    return username, password

# ---------------- Customer CRUD (Updated with correct recent CSV columns) ----------------
def get_all_customers(active_only=False):
    df = _load_csv(CUSTOMERS_CSV)
    if df.empty:
        return []
    if active_only:
        df = df[df['status'] == 'active']
    return df.to_dict(orient='records')

def add_customer(name, phone, address, due, category="Regular", email=""):
    df = _load_csv(CUSTOMERS_CSV)
    new_id = (df['id'].max() or 0) + 1 if not df.empty else 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate credentials
    username, password = _generate_credentials()
    
    cust = {
        "id": new_id, "name": name, "phone": phone, "email": email,
        "address": address, "due": float(due), "category": category,
        "status": "active", "last_update": now_str, "added_at": now_str,
        "username": username, "password": generate_password_hash(password)
    }
    
    # Save to main CSV
    df = pd.concat([df, pd.DataFrame([cust])], ignore_index=True)
    _save_csv(df, CUSTOMERS_CSV)
    
    # Append to added_customers.csv with only intended columns
    _append_csv(ADDED_CSV, {
        "id": new_id, "name": name, "phone": phone, "email": email,
        "address": address, "due": float(due), "last_update": now_str,
        "status": "active", "added_at": now_str
    })
    
    # Append to dues.csv
    _append_csv(DUES_CSV, {
        "id": new_id, "name": name, "phone": phone,
        "address": address, "due_amount": float(due),
        "due_date": datetime.now().date(), "last_message_date": ""
    })
    
    return {**cust, "password": password}  # Return plain password for email

def reset_credentials(customer_id, new_username=None, new_password=None):
    """NEW: Allow admin to reset customer credentials"""
    df = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df['id'].values:
        return None
        
    cust = df[df['id'] == customer_id].iloc[0].to_dict()
    updates = {}
    
    if new_username:
        updates['username'] = new_username
    if new_password:
        updates['password'] = generate_password_hash(new_password)
    
    if updates:
        updates['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[df['id'] == customer_id, list(updates.keys())] = list(updates.values())
        _save_csv(df, CUSTOMERS_CSV)
    
    return {
        **cust,
        **updates,
        "password": new_password if new_password else "[unchanged]"
    }

def update_due(customer_id, new_due):
    df = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df['id'].values:
        return None
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.loc[df["id"] == customer_id, ["due", "last_update"]] = [float(new_due), now_str]
    _save_csv(df, CUSTOMERS_CSV)
    cust = df[df['id'] == customer_id].iloc[0].to_dict()
    
    # Append to updated_customers.csv with only intended columns
    _append_csv(UPDATED_CSV, {
        "id": cust["id"], "name": cust["name"], "phone": cust["phone"],
        "email": cust["email"], "address": cust["address"], "due": cust["due"],
        "last_update": cust["last_update"], "status": cust["status"],
        "updated_due": float(new_due), "updated_at": now_str
    })
    
    # Sync with dues
    update_due_record(customer_id, new_due)
    return cust


def record_partial_payment(customer_id, amount):
    df = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df['id'].values:
        return None
    cust = df[df['id'] == customer_id].iloc[0].to_dict()
    new_due = float(cust['due']) - float(amount)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.loc[df['id'] == customer_id, ["due", "last_update"]] = [new_due, now_str]
    _save_csv(df, CUSTOMERS_CSV)
    
    # Append to partial_customers.csv with only intended columns
    _append_csv(PARTIAL_CSV, {
        "id": cust["id"], "name": cust["name"], "phone": cust["phone"],
        "email": cust["email"], "address": cust["address"], "due": cust["due"],
        "last_update": cust["last_update"], "status": cust["status"],
        "partial_due": new_due, "partial_at": now_str
    })
    
    # Sync with dues
    update_due_record(customer_id, new_due, last_message_date=now_str)
    cust.update({"due": new_due, "partial_due": new_due, "partial_at": now_str})
    return cust


def delete_customer(customer_id):
    df = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df['id'].values:
        return None
    cust = df[df['id'] == customer_id].iloc[0].to_dict()
    df = df[df['id'] != customer_id]
    _save_csv(df, CUSTOMERS_CSV)
    
    # Append to deleted_customers.csv with only intended columns
    _append_csv(DELETED_CSV, {
        "id": cust["id"], "name": cust["name"], "phone": cust["phone"],
        "email": cust["email"], "address": cust["address"], "due": cust["due"],
        "last_update": cust["last_update"], "status": "deleted",
        "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Remove from dues
    df_dues = _load_csv(DUES_CSV)
    df_dues = df_dues[df_dues['id'] != customer_id]
    _save_csv(df_dues, DUES_CSV)
    return cust

def delete_all_customers():
    df = _load_csv(CUSTOMERS_CSV)
    if df.empty:
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in df.iterrows():
        _append_csv(DELETED_CSV, {
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "email": row["email"],
            "address": row["address"],
            "due": row["due"],
            "last_update": row["last_update"],
            "status": "deleted",
            "deleted_at": now_str
        })
    _save_csv(pd.DataFrame(columns=df.columns), CUSTOMERS_CSV)
    _save_csv(pd.DataFrame(columns=_load_csv(DUES_CSV).columns), DUES_CSV)

def update_due_record(customer_id, new_due, last_message_date=None):
    df = _load_csv(DUES_CSV)
    if customer_id not in df['id'].values:
        return
    df.loc[df['id'] == customer_id, 'due_amount'] = new_due
    if last_message_date:
        df.loc[df['id'] == customer_id, 'last_message_date'] = last_message_date
    else:
        df.loc[df['id'] == customer_id, 'last_message_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_csv(df, DUES_CSV)



def get_recent_activity(limit=5):
    logs = [
        (ADDED_CSV, "added_at"),
        (UPDATED_CSV, "updated_at"),
        (PARTIAL_CSV, "partial_at"),
        (DELETED_CSV, "deleted_at")
    ]
    recent_records = []
    for path, ts_col in logs:
        df = _load_csv(path)
        if not df.empty and ts_col in df.columns:
            df[ts_col] = pd.to_datetime(df[ts_col], errors='coerce')
            recent_records.append(df)
    if not recent_records:
        return []
    combined = pd.concat(recent_records, ignore_index=True)
    
    # Determine a single timestamp column to sort
    for col in ['added_at', 'updated_at', 'partial_at', 'deleted_at']:
        if col in combined.columns:
            combined['timestamp'] = pd.to_datetime(combined[col], errors='coerce')
            break
    combined = combined.sort_values(by='timestamp', ascending=False)
    return combined.head(limit).to_dict(orient='records')

# ---------------- Enhanced Authentication (Updated) ----------------

def login_user(username, password):
    """Customer-only login (no legacy user fallback)"""
    customers_df = _load_csv(CUSTOMERS_CSV)
    
    if not customers_df.empty:
        user = customers_df[
            (customers_df['username'].str.strip() == username.strip()) &  # Changed
            (customers_df['status'] == 'active')
        ]
        
        if not user.empty and check_password_hash(user.iloc[0]['password'].strip(), password.strip()):  # Changed
            customer_data = user.iloc[0]
            _append_csv(SIGNIN_LOGS_CSV, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "customer_id": customer_data['id'],
                "username": username,
                "name": customer_data['name'],
                "login_type": "customer"
            })
            return {
                "success": True,
                "customer_id": customer_data['id'],
                "name": customer_data['name'],
                "due": customer_data['due'],
                "email": customer_data['email'],
                "phone": customer_data['phone']
            }
    
    return {"success": False, "message": "Invalid credentials"}
    
# ---------------- User Payments / Delete (Unchanged) ----------------
def user_pay_due(username, customer_id, amount):
    df_cust = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df_cust['id'].values:
        return None
    cust = df_cust[df_cust['id']==customer_id].iloc[0].to_dict()
    new_due = float(cust['due']) - float(amount)
    df_cust.loc[df_cust['id']==customer_id, ['due', 'last_update']] = [new_due, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    _save_csv(df_cust, CUSTOMERS_CSV)
    update_due_record(customer_id, new_due)
    # Log user payment
    _append_csv(USER_PAYMENT_CSV, {"id": customer_id, "username": username, "name": cust['name'],
                                   "amount_paid": amount, "new_due": new_due, "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return {**cust, "due": new_due}

def user_delete_account(username, customer_id):
    df_cust = _load_csv(CUSTOMERS_CSV)
    if customer_id not in df_cust['id'].values:
        return None
    cust = df_cust[df_cust['id']==customer_id].iloc[0].to_dict()
    if float(cust['due']) > 0:
        return None  # Cannot delete if due remains
    # Delete customer
    df_cust = df_cust[df_cust['id'] != customer_id]
    _save_csv(df_cust, CUSTOMERS_CSV)
    # Remove from dues
    df_dues = _load_csv(DUES_CSV)
    df_dues = df_dues[df_dues['id'] != customer_id]
    _save_csv(df_dues, DUES_CSV)
    # Log user deletion
    _append_csv(USER_DELETED_CSV, {"id": customer_id, "username": username, "name": cust['name'], "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return cust

# ---------------- Admin: View User Transactions (Unchanged) ----------------
def get_user_transactions(limit=10):
    payments = _load_csv(USER_PAYMENT_CSV)
    deletions = _load_csv(USER_DELETED_CSV)
    combined = pd.concat([payments, deletions], ignore_index=True) if not payments.empty or not deletions.empty else pd.DataFrame()
    if combined.empty:
        return []
    combined['timestamp'] = pd.to_datetime(
        combined.get('payment_date').where(combined.get('payment_date').notna(), combined.get('deleted_at')),
        errors='coerce'
    )
    combined = combined.sort_values(by='timestamp', ascending=False)
    return combined.head(limit).to_dict(orient='records')