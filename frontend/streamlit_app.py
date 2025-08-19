API_BASE = "http://127.0.0.1:5000"
import streamlit as st
import pandas as pd
import os, re
from datetime import datetime
import requests
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.notifications.email_service import send_email, shop_name
from backend import services  # for new user/payment functionalities

# ---------------- Paths ----------------
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'data'))
CUSTOMERS_CSV = os.path.join(DATA_PATH, 'customers.csv')
ADDED_CSV = os.path.join(DATA_PATH, 'added_customers.csv')
UPDATED_CSV = os.path.join(DATA_PATH, 'updated_customers.csv')
PARTIAL_CSV = os.path.join(DATA_PATH, 'partial_customers.csv')
DELETED_CSV = os.path.join(DATA_PATH, 'deleted_customers.csv')
DUES_CSV = os.path.join(DATA_PATH, 'dues.csv')
LOGS_CSV = os.path.join(DATA_PATH, 'logs.csv')
SIGNUP_CSV = os.path.join(DATA_PATH, 'signup.csv')
SIGNIN_CSV = os.path.join(DATA_PATH, 'signin.csv')
USER_PAYMENT_CSV = os.path.join(DATA_PATH, 'user_payment_updated.csv')
USER_DELETED_CSV = os.path.join(DATA_PATH, 'user_account_deleted.csv')

st.set_page_config(layout="wide")
st.title("Customer Due Tracker System")

# ---------------- Session State ----------------
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "tab" not in st.session_state:
    st.session_state.tab = None
if "logged_in" not in st.session_state:  # NEW
    st.session_state.logged_in = False

# ---------------- Helper Functions ----------------
def append_csv(file, row):
    pd.DataFrame([row]).to_csv(file, mode='a', header=not os.path.exists(file), index=False)

def load_csv(file, cols=None):
    if not os.path.exists(file):
        return pd.DataFrame(columns=cols or [])
    try:
        df = pd.read_csv(file, sep=",", engine="python", on_bad_lines='skip', quoting=3)
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return pd.DataFrame(columns=cols or [])

def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.tab = None
    st.success("Logged out successfully!")
    st.rerun()  

def load_customers():
    cols = ['id', 'name', 'phone', 'email', 'address', 'due', 
            'username', 'password', 'last_update', 'status']
    df = load_csv(CUSTOMERS_CSV, cols)
    for c in ['id', 'due']:
        if c in df: df[c] = pd.to_numeric(df[c], errors='coerce')
    for col in ['phone', 'email', 'name', 'address', 'status', 'last_update', 'username', 'password']:
        if col in df: df[col] = df[col].fillna('').astype(str)
    return df

def save_customers(df):
    os.makedirs(DATA_PATH, exist_ok=True)
    df.to_csv(CUSTOMERS_CSV, index=False)

def log_action(func, msg, *args, **kwargs):
    append_csv(LOGS_CSV, {"timestamp": datetime.now(), "function": func, "message": msg,
                           "args": str(args), "kwargs": str(kwargs)})

def valid_email(email):
    return bool(email and re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email.strip()))

def valid_phone(phone):
    return phone.isdigit() and len(phone) == 10

def validate_customer(name, phone, email, customers):
    name, phone, email = name.strip(), phone.strip(), email.strip()
    if not all([name, phone, email]):
        st.error("All fields are required")
        return False
    if not valid_phone(phone):
        st.error("Phone must be exactly 10 digits.")
        return False
    if not valid_email(email):
        st.error("Invalid email format.")
        return False
    for c in customers.itertuples():
        if c.name.strip().lower() == name.lower():
            st.error("Name already exists.")
            return False
        if c.phone.strip() == phone:
            st.error("Phone already exists.")
            return False
        if c.email.strip().lower() == email.lower():
            st.error("Email already exists.")
            return False
    return True

# --------------- Login Block ---------------
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Admin Login", "👤 Customer Login"])
    
    with tab1:
        with st.form("admin_login"):
            st.header("Admin Sign In")
            admin_user = st.text_input("Admin Username")
            admin_pass = st.text_input("Admin Password", type="password")
            
            if st.form_submit_button("Login as Admin"):
                if admin_user == "admin" and admin_pass == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = "admin"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials")
    
    with tab2:
        with st.form("user_login"):
            st.header("Customer Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
        
            if st.form_submit_button("Login as Customer"):
                login_result = services.login_user(username, password)
                if login_result.get("success"):
                    st.session_state.logged_in = True
                    st.session_state.role = "user"
                    st.session_state.username = username
                    st.session_state.customer_id = login_result["customer_id"]
                    st.session_state.customer_name = login_result["name"]
                    st.session_state.customer_due = login_result["due"]
                    st.success(f"Welcome {login_result['name']}!")
                    st.rerun()
                else:
                    st.error(login_result["message"])  # Changed to show exact message

# ---------------- ---------- LOGGED IN ----------------
else:
    role = st.session_state.role
    username = st.session_state.username
    
    # NEW Logout Button (add at top of sidebar)
    if st.sidebar.button("🚪 Logout"):
        logout_user()
    
    # Rest of your existing tab code stays exactly the same...
    if role == "admin":
        tabs = {
            "➕ Add Customer": "add",
            "🔑 Manage Credentials": "credentials",
            "✏️ Update / Partial Payment": "update_partial",
            "🗑️ Delete Customer": "delete",
            "⚙️ Payment Settings (Razorpay)": "payment_settings",  # ✅ added here
            "📋 View All": "view",
            "📊 Summary": "summary",
            "🕒 Recent Activity": "recent",
            "💳 User Transactions": "user_transactions"
        }
    elif role == "user":
        tabs = {
            "💰 Pay Due": "pay_due",
            "🗑️ Delete Account": "delete_account"
        }

    if "tab" not in st.session_state:
        st.session_state.tab = list(tabs.keys())[0]
    for icon in tabs:
        if st.sidebar.button(icon, use_container_width=True):
            st.session_state.tab = icon
    choice = st.session_state.tab

    # ---------------- ---------- ADMIN TABS ----------------
    if role == "admin":
        # ---------- Add Customer ----------
        if choice == "➕ Add Customer":
            st.header("➕ Add Customer")
            name = st.text_input("Name *").strip()
            phone = st.text_input("Phone *").strip()
            email = st.text_input("Email *").strip()
            address = st.text_input("Address").strip()
            due = st.number_input("Due Amount", min_value=0.0, format="%.2f")

            if st.button("Add Customer"):
                df = load_customers()
                if validate_customer(name, phone, email, df):
                    new_id = (df['id'].max() or 0) + 1 if not df.empty else 1
                    now = datetime.now()

                    # Generate secure random credentials
                    import secrets
                    import string
                    from werkzeug.security import generate_password_hash

                    username = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
                    plain_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
                    hashed_password = generate_password_hash(plain_password)

                    new_cust = {
                        "id": new_id,
                        "name": name,
                        "phone": phone,
                        "email": email,
                        "address": address,
                        "due": float(due),
                        "username": username,
                        "password": hashed_password,
                        "plain_password": plain_password,
                        "last_update": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "active",
                        "added_at": now.strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # Add to main customers CSV
                    df = pd.concat([df, pd.DataFrame([new_cust])], ignore_index=True)
                    save_customers(df)

                    # Add to added_customers.csv (only allowed columns)
                    append_csv(ADDED_CSV, {
                        "id": new_cust["id"],
                        "name": new_cust["name"],
                        "phone": new_cust["phone"],
                        "email": new_cust["email"],
                        "address": new_cust["address"],
                        "due": new_cust["due"],
                        "last_update": new_cust["last_update"],
                        "status": new_cust["status"],
                        "added_at": new_cust["added_at"]
                    })

                    # Add to dues.csv
                    append_csv(DUES_CSV, {
                        "id": new_id,
                        "name": name,
                        "phone": phone,
                        "address": address,
                        "due_amount": float(due),
                        "due_date": now.date(),
                        "last_message_date": ""
                    })

                    # Log the action
                    log_action("add_customer", f"Added {name}", name, phone, address)

                    # Send email
                    try:
                        send_email(
                            email,
                            f"Welcome to {shop_name}!",
                            f"""
        Hello {name},

        This is an important notification from {shop_name} regarding your new account:

        Your account has been successfully created with these credentials:
        📄 Name: {name}  
        📞 Phone: {phone}  
        📍 Address: {address}  
        💰 Current Due: ₹{due:.2f}
        🔐 Username: {username}
        🔐 Password: {plain_password}

        💰 Initial Due Amount: ₹{due:.2f}

        Please log in and change your password immediately for security.
        If you have any questions or concerns, do not hesitate to reach out to us.

        Thank you for choosing {shop_name}.

        Warm regards,
        {shop_name} Team
        """
                        )
                        st.success(f"Customer '{name}' added! Username: {username} | Password: {plain_password}")
                    except Exception as e:
                        st.warning(f"Customer added but email failed: {e}")



        # ---------- Manage Credentials ----------
        elif choice == "🔑 Manage Credentials":
            st.header("🔑 Customer Credential Management")
            df = load_customers()

            # Select customer
            customer = st.selectbox("Select Customer", 
                                df[df['status'] == 'active']['name'].tolist())

            if customer:
                cust_data = df[df['name'] == customer].iloc[0]
                st.write(f"Current credentials for {customer}:")
                st.code(f"Username: {cust_data['username']}\nPassword: {cust_data['password']}")

                # Credential reset
                with st.expander("🔧 Reset Credentials"):
                    with st.form("reset_creds"):
                        new_username = st.text_input("New Username", value=cust_data['username'])
                        new_password = st.text_input("New Password", value=cust_data['password'])
        
                        if st.form_submit_button("Update Credentials"):
                            from werkzeug.security import generate_password_hash
                            import os
                            import pandas as pd
                            from datetime import datetime

                            hashed_password = generate_password_hash(new_password)
                    
                            # Save old credentials
                            old_username = cust_data['username']
                            old_password = cust_data['password']

                            # Update main customer dataframe
                            df.loc[df['name'] == customer, 'username'] = new_username
                            df.loc[df['name'] == customer, 'password'] = hashed_password
                            df.loc[df['name'] == customer, 'last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
                            save_customers(df)

                            # Append to reset.csv
                            reset_file = r"D:\Projects\Customer_Due_Tracker_System\backend\data\reset.csv"
                            reset_entry = pd.DataFrame([{
                                "id": cust_data['id'],
                                "name": customer,
                                "old_username": old_username,
                                "old_password": old_password,
                                "new_username": new_username,
                                "new_password": hashed_password,   # store hashed password
                                "plain_password": new_password     # store plain password for reference
                            }])
                            if os.path.exists(reset_file):
                                reset_entry.to_csv(reset_file, mode='a', index=False, header=False)
                            else:
                                reset_entry.to_csv(reset_file, index=False)

                            try:
                                send_email(
                                    cust_data['email'],
                                    f"Important Account Update from {shop_name}",
                                    f"""
        Hello {customer},

        This is an important notification from {shop_name} regarding your account credentials:

        Your login information has been updated by the administrator.
        🔐 New Username: {new_username}
        🔐 New Password: {new_password}

        For security reasons, we recommend:
        1. Logging in immediately to verify access
        2. Changing your password after first login

        If you did not request this change or have any questions, please contact us immediately.

        Thank you for being a valued customer.

        Warm regards,
        {shop_name} Team
        """
                                )
                                st.success("Credentials updated and customer notified!")
                            except Exception as e:
                                st.warning(f"Credentials updated but email failed: {e}")


# ---------- Update / Partial Payment ----------
        elif choice == "✏️ Update / Partial Payment":
            st.header("👨‍🔧 Update or Partial Payment")
            df = load_customers()
            if df.empty:
                st.info("No customers available.")
            else:
                cust_id = st.number_input("Enter Customer ID", min_value=1, step=1)
                if cust_id not in df['id'].values:
                    st.warning("Customer ID not found.")
                else:
                    cust = df[df["id"] == cust_id].iloc[0]
                    current_due = float(cust['due'])
                    st.write(f"Name: {cust['name']}, Current Due: ₹{current_due:.2f}")
                    
                    # Choose action
                    action = st.radio("Choose action:", ["Update Due", "Partial Payment"])
                    
                    if action == "Update Due":
                        new_due = st.number_input("Enter New Due Amount", min_value=0.0, value=current_due, format="%.2f")
                        if st.button("Submit Update"):
                            now_ts = pd.Timestamp.now()
                            df.loc[df["id"] == cust_id, ["due", "last_update"]] = [new_due, now_ts]
                            save_customers(df)
                            
                            # Append to updated_customers.csv (only allowed columns)
                            append_csv(UPDATED_CSV, {
                                "id": cust["id"],
                                "name": cust["name"],
                                "phone": cust["phone"],
                                "email": cust["email"],
                                "address": cust["address"],
                                "due": cust["due"],
                                "last_update": now_ts.strftime("%Y-%m-%d %H:%M:%S"),
                                "status": cust["status"],
                                "updated_due": new_due,
                                "updated_at": now_ts.strftime("%Y-%m-%d %H:%M:%S")
                            })

                            # Update dues.csv
                            dues_df = load_csv(DUES_CSV)
                            dues_df.loc[dues_df['id'] == cust_id, ['due_amount', 'last_message_date']] = [new_due, now_ts]
                            dues_df['last_message_date'] = pd.to_datetime(dues_df['last_message_date'], errors='coerce')\
                                                            .dt.strftime("%Y-%m-%d %H:%M:%S")
                            dues_df.to_csv(DUES_CSV, index=False)

                            log_action("update_due", f"Updated due for ID={cust_id}", cust_id, new_due)
                            st.success(f"Due updated to ₹{new_due:.2f} successfully!")

                            # Email notification
                            try:
                                send_email(
                                    cust['email'],
                                    "Important Update on Your Account Due",
                                    f"""Hello {cust['name']},

This is an important notification from {shop_name} regarding your account:

Your current outstanding due has been updated by the admin. 
💰 Previous Due: ₹{current_due:.2f}
💰 Updated Due: ₹{new_due:.2f}

Please make sure to check your account and plan your payment accordingly.

Thank you for being a valued customer.

Warm regards,
{shop_name} Team
"""
                                )
                            except Exception as e:
                                st.warning(f"Failed to send email: {e}")

                    elif action == "Partial Payment":
                        payment_amount = st.number_input(
                            "Enter Payment Amount", min_value=0.0, max_value=current_due, value=0.0, format="%.2f"
                        )
                        if st.button("Submit Payment"):
                            now_ts = pd.Timestamp.now()
                            new_due = current_due - payment_amount

                            df.loc[df["id"] == cust_id, ["due", "last_update"]] = [new_due, now_ts]
                            save_customers(df)

                            # Append to partial_customers.csv (only allowed columns)
                            append_csv(PARTIAL_CSV, {
                                "id": cust["id"],
                                "name": cust["name"],
                                "phone": cust["phone"],
                                "email": cust["email"],
                                "address": cust["address"],
                                "due": cust["due"],
                                "last_update": now_ts.strftime("%Y-%m-%d %H:%M:%S"),
                                "status": cust["status"],
                                "partial_due": new_due,
                                "partial_at": now_ts.strftime("%Y-%m-%d %H:%M:%S")
                            })

                            # Update dues.csv
                            dues_df = load_csv(DUES_CSV)
                            dues_df.loc[dues_df['id'] == cust_id, ['due_amount', 'last_message_date']] = [new_due, now_ts]
                            dues_df['last_message_date'] = pd.to_datetime(dues_df['last_message_date'], errors='coerce')\
                                                            .dt.strftime("%Y-%m-%d %H:%M:%S")
                            dues_df.to_csv(DUES_CSV, index=False)

                            log_action("partial_payment", f"Partial payment for ID={cust_id}", cust_id, payment_amount)
                            st.success(f"Partial payment of ₹{payment_amount:.2f} applied. New due: ₹{new_due:.2f}")

                            # Email notification
                            try:
                                send_email(
                                    cust['email'],
                                    "Partial Payment Received",
                                    f"""Hello {cust['name']},

Thank you for your recent payment to {shop_name}!

💰 Previous Due: ₹{current_due:.2f}
💰 Payment Received: ₹{payment_amount:.2f}
💰 Remaining Due: ₹{new_due:.2f}

We appreciate your prompt payment. Please continue to monitor your account
and make timely payments to avoid any inconvenience.

If you have any questions, our support team is here to help.

Warm regards,
{shop_name} Team
"""
                                )
                            except Exception as e:
                                st.warning(f"Failed to send email: {e}")

                        # -------- CASE 3: No Change --------
                        else:
                            st.info("No change in due amount.")


# ---------- Delete Customer ----------
        elif choice == "🗑️ Delete Customer":
            st.header("🗑️ Delete Customer")
            df = load_customers()

            if df.empty:
                st.info("No customers available.")
            else:
                # --- Single Customer Delete ---
                st.subheader("Delete Single Customer")
                cust_id = st.number_input("Enter Customer ID to Delete", min_value=1, step=1)

                if cust_id not in df['id'].values:
                    st.warning("Customer ID not found.")
                else:
                    cust = df[df["id"] == cust_id].iloc[0]
                    st.write(f"Name: {cust['name']}, Current Due: ₹{cust['due']:.2f}")

                    if st.button("Delete Customer"):
                        # Remove from customers CSV
                        df = df[df["id"] != cust_id]
                        save_customers(df)

                        # Append to deleted CSV (only allowed columns)
                        deleted_row = {
                            "id": cust["id"],
                            "name": cust["name"],
                            "phone": cust["phone"],
                            "email": cust["email"],
                            "address": cust["address"],
                            "due": cust["due"],
                            "last_update": cust["last_update"],
                            "status": "deleted",
                            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        append_csv(DELETED_CSV, deleted_row)
                        log_action("delete_customer", f"Deleted ID={cust_id}", cust_id)

                        # Remove from dues CSV
                        dues_df = load_csv(DUES_CSV)
                        dues_df = dues_df[dues_df['id'] != cust_id]
                        dues_df.to_csv(DUES_CSV, index=False)

                        st.success(f"Customer '{cust['name']}' deleted successfully!")

                        # ----------- SEND EMAIL -----------
                        try:
                            send_email(
                                cust['email'],
                                f"Account Deletion Notice - {shop_name}",
                                f"""
Hello {cust['name']},

This is to notify you that your account with {shop_name} has been permanently deleted from our system.

📄 Customer Details:
Name: {cust['name']}
Phone: {cust['phone']}
Address: {cust['address']}
Final Due: ₹{cust['due']:.2f}

If this action was a mistake or you wish to reinstate your account, 
please contact us immediately.

We value all our customers and are here to support you in case of any issues.

Warm regards,
{shop_name} Team
"""
                            )
                        except Exception as e:
                            st.warning(f"Failed to send email: {e}")

                # --- Delete ALL Customers ---
                st.subheader("Delete ALL Customers")
                st.warning("⚠️ This will delete ALL customer records permanently!")

                if st.button("Delete ALL Customers"):
                    for _, row in df.iterrows():
                        deleted_row = {
                            "id": row["id"],
                            "name": row["name"],
                            "phone": row["phone"],
                            "email": row["email"],
                            "address": row["address"],
                            "due": row["due"],
                            "last_update": row["last_update"],
                            "status": "deleted",
                            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        append_csv(DELETED_CSV, deleted_row)

                        # Remove from dues.csv
                        dues_df = load_csv(DUES_CSV)
                        dues_df = dues_df[dues_df['id'] != row['id']]
                        dues_df.to_csv(DUES_CSV, index=False)

                        # Log each deletion
                        log_action("delete_customer", f"Deleted ID={row['id']}", row['id'])

                        try:
                            send_email(
                                deleted_row['email'],
                                f"Account Deletion Notice - {shop_name}",
                                f"""
Hello {deleted_row['name']},

We regret to inform you that your account with {shop_name} has been removed from our system.

📄 Customer Details:
Name: {deleted_row['name']}
Phone: {deleted_row['phone']}
Address: {deleted_row['address']}
Final Due: ₹{deleted_row['due']:.2f}

If you believe this action was taken in error or wish to reinstate your account, 
please contact us as soon as possible.

We sincerely apologize for any inconvenience this may cause.

Kind regards,
{shop_name} Team
"""
                            )
                        except Exception as e:
                            st.warning(f"Failed to send email: {e}")

                    # Clear customers CSV
                    save_customers(pd.DataFrame(columns=df.columns))
                    log_action("delete_all_customers", "Deleted all customers")
                    st.success("✅ All customers deleted successfully!")

            # ---------- Razorpay Payment Settings ----------
        elif choice == "⚙️ Payment Settings (Razorpay)":
            st.header("Razorpay Payment Settings")
            key_id = st.text_input("Key ID", value="rzp_test_ABC123")
            key_secret = st.text_input("Key Secret", type="password", value="xyz_test_123")
            if st.button("Save Keys"):
                res = requests.post(f"http://127.0.0.1:5000/api/admin/save_keys", json={
                    "key_id": key_id, "key_secret": key_secret
                })
                if res.status_code == 200:
                    try:
                        data = res.json()
                        st.success("✅ Keys saved successfully")
                    except ValueError:
                        st.error("❌ Server did not return valid JSON")
                else:
                    try:
                        error_msg = res.json().get("error", "❌ Failed to save keys")
                    except ValueError:
                        error_msg = f"❌ Failed to save keys (status {res.status_code})"
                    st.error(error_msg)




# ---------- View All ----------  
        elif choice == "📋 View All":
            st.header("📋 View Customers")
            df = load_csv(CUSTOMERS_CSV)
            dues_df = load_csv(DUES_CSV)  # Load dues.csv

            if df.empty:
                st.info("No customer records found.")
            else:
                # Merge dues with customer data
                df = df.merge(dues_df[['id', 'due_date', 'due_amount']], left_on='id', right_on='id', how='left')

                # Remove password and due_amount columns before display
                display_df = df.drop(columns=['password', 'due_amount'], errors='ignore')

                # Row coloring based on due_date
                def highlight_due_date(row):
                    if pd.notna(row['due_date']):
                        days_due = (pd.Timestamp.now() - pd.to_datetime(row['due_date'], errors='coerce')).days
                        if days_due >= 45:
                            return ['background-color: red']*len(row)
                        elif days_due >= 30:
                            return ['background-color: orange']*len(row)
                        elif days_due >= 15:
                            return ['background-color: yellow']*len(row)
                    return ['']*len(row)

                st.dataframe(display_df.style.apply(highlight_due_date, axis=1))

                # Custom alert message for customers with due_date ≥ 15 days
                due_customers = df[pd.notna(df['due_date'])].copy()
                due_customers['days_due'] = (pd.Timestamp.now() - pd.to_datetime(due_customers['due_date'], errors='coerce')).dt.days
                due_customers = due_customers[due_customers['days_due'] >= 15][['name', 'phone', 'due_date', 'days_due']]

                if not due_customers.empty:
                    st.markdown("### ⚠️ Customers with Significant Dues (≥ 15 / ≥ 30 / ≥ 45 days)")

                    for _, row in due_customers.iterrows():
                        last_update = pd.to_datetime(row['due_date'], errors='coerce')
                        days_due = row['days_due'] if not pd.isna(last_update) else "N/A"

                        if days_due >= 45:
                            dot = "🔴"
                            urgency = "<b>Immediate action is recommended!</b>"
                        elif days_due >= 30:
                            dot = "🟠"
                            urgency = "<b>Please follow up soon!</b>"
                        else:  # days_due >= 15
                            dot = "🟡"
                            urgency = "<b>Kindly remind the customer.</b>"

                        st.markdown(
                            f"<p style='font-size:18px;'>{dot} Customer <b>{row['name']}</b> with phone 📞 <b>{row['phone']}</b> "
                            f"has an outstanding due since <b>{last_update.strftime('%d %b %Y') if not pd.isna(last_update) else 'N/A'}</b> "
                            f"(Overdue: <b>{days_due} days</b>). {urgency}</p>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No customers have dues ≥ 15 days.")


        # ---------- Summary ----------
        elif choice == "📊 Summary":
            st.subheader("📊 Analytics Dashboard")
            API = "http://localhost:5000"  # Flask backend
            try:
                r = requests.get(f"{API}/api/admin/customers?active_only=true")
                if r.status_code == 200:
                    data = r.json()
                else:
                    st.error(f"Backend returned status {r.status_code}")
                    st.stop()

                if data:
                    df = pd.DataFrame(data)
                    st.metric("👥 Total Customers", len(df))
                    st.metric("💰 Total Outstanding Due", f"₹{df['due'].sum():,.2f}")
            
                    paid_count = len(df[df['due'] == 0])
                    unpaid_count = len(df[df['due'] > 0])
                    
                    st.write("### 🧾 Paid vs Unpaid")
                    st.plotly_chart({"data":[{"values":[paid_count, unpaid_count],
                                      "labels":["Paid","Unpaid"],"type":"pie"}]})
            
                    st.write("### 📍 Top 5 Debtors")
                    top_df = df[df['due']>0].nlargest(5,'due')[['name','due']]
                    st.table(top_df.set_index('name'))
                else:
                    st.info("No customer data available")
            except Exception as e:
                st.error(f"Failed to fetch summary from backend API. Error: {e}")


# ---------- Recent Activity ----------
        elif choice == "🕒 Recent Activity":
            st.header("🕒 Recent Activity")
            logs = [
                (ADDED_CSV, "Recently Added"),
                (UPDATED_CSV, "Recently Updated Dues"),
                (PARTIAL_CSV, "Partial Payments"),
                (DELETED_CSV, "Deleted Customers")
            ]
            for path, label in logs:
                df = load_csv(path)
                st.markdown(f"**{label}:**")
                st.dataframe(df.tail(5).iloc[::-1] if not df.empty else pd.DataFrame({"Info":["No records found"]}))

        # ---------------- User Transactions ----------------
        elif choice == "💳 User Transactions":
            st.header("📜 Transaction History", divider="rainbow")
    
            try:
                # Load both payment and deletion records
                payments_df = load_csv(USER_PAYMENT_CSV)
                deleted_df = load_csv(USER_DELETED_CSV)
        
                # Combine both data sources
                all_transactions = []
        
                # Process payments
                if not payments_df.empty:
                    for _, row in payments_df.iterrows():
                        all_transactions.append({
                            'timestamp': row.get('payment_date', ''),
                            'c_name': row.get('name', ''),
                            'id': row.get('id', ''),
                            'type': 'payment',
                            'amount': row.get('amount_paid', 0),
                            'remaining_due': row.get('remaining_due', 0)
                        })
        
                # Process account deletions
                if not deleted_df.empty:
                    for _, row in deleted_df.iterrows():
                        all_transactions.append({
                            'timestamp': row.get('deleted_at', ''),
                            'c_name': row.get('name', ''),
                            'id': row.get('id', ''),
                            'type': 'deletion',
                            'amount': row.get('final_payment', 0)
                        })
        
                if not all_transactions:
                    st.info("📭 No transaction records found yet")
                else:
                    # Sort by timestamp (newest first)
                    all_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
            
                    # Display each transaction with bigger text
                    for trans in all_transactions:
                        if trans['type'] == 'payment':
                            st.markdown(
                                f"""<p style='font-size:18px; line-height:2.0;'>
                                💸 <strong>Payment Received</strong> by this customer named <strong>{trans['c_name']}</strong> 
                                has paid the due of <strong>₹{trans['amount']:.2f}</strong> at ⏰ <em>{trans['timestamp']}</em>
                                </p>""",
                                unsafe_allow_html=True
                            )
                        elif trans['type'] == 'deletion':
                            st.markdown(
                                f"""<p style='font-size:18px; line-height:2.0;'>
                                🚪 <strong>Account Closed</strong> by this customer named <strong>{trans['c_name']}</strong> 
                                after paying all dues of <strong>₹{trans['amount']:.2f}</strong> at ⏰ <em>{trans['timestamp']}</em>
                                </p>""",
                                unsafe_allow_html=True
                            )
                        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)  # styled divider
                
            except Exception as e:
                st.error(f"⚠️ Error loading transactions: {str(e)}")

    # ---------------- USER TABS ----------------
    else:
        df = load_customers()

# ---------- User Pay Due ----------
        if choice == "💰 Pay Due":
            st.header("💰 Pay Your Due")
            if 'customer_id' not in st.session_state:       
                st.warning("Please login first")
            else:
                cust_id = st.session_state.customer_id
                current_due = st.session_state.customer_due

                st.write(f"""
                **Account Summary:**
                - Name: {st.session_state.customer_name}
                - Current Due: ₹{current_due:.2f}
                """)

                upi_id = st.text_input("Enter your UPI ID (e.g., name@upi)")

                if st.button("Pay Now"):
                    if not upi_id:
                        st.error("Please enter a valid UPI ID")
                    else:
                        res = requests.post(f"{API_BASE}/api/customer/pay", json={
                            "upi_id": upi_id,
                            "amount": current_due
                        })

                        if res.status_code == 200:
                            order = res.json()
                            st.success("✅ Payment request created. Please approve in your UPI app.")
                            payment_id = order.get("id")

                            with st.spinner("⏳ Waiting for payment confirmation..."):
                                import time
                                for _ in range(10):  # poll 10 times
                                    time.sleep(5)
                                    status_res = requests.get(f"{API_BASE}/api/payment/status/{payment_id}")
                                    if status_res.status_code == 200:
                                        status = status_res.json().get("status")
                                        if status == "captured":
                                            st.success("🎉 Payment Successful!")
                                            st.session_state.customer_due = 0
                                            break
                                        elif status == "failed":
                                            st.error("❌ Payment Failed")
                                            break
                                else:
                                    st.warning("⏳ Payment still pending. Please check your UPI app.")
                        else:
                            try:
                                st.error(res.json().get("error", "❌ Failed to start payment"))
                            except:
                                st.error("❌ Failed to start payment (invalid server response)")


        # ---------- User Delete Account ----------
        elif choice == "🗑️ Delete Account":
            st.header("🗑️ Delete Your Account")
            if 'customer_id' not in st.session_state:
                st.warning("Please login first")
            else:
                cust_id = st.session_state.customer_id
                current_due = st.session_state.customer_due
        
                st.write(f"""
                **Account Details:**
                - Name: {st.session_state.customer_name}
                - Current Due: ₹{current_due:.2f}
                """)

                if float(current_due) > 0:
                    st.error("Cannot delete account with outstanding dues")
                else:
                    st.warning("""
                    ⚠️ This will permanently delete your account!
                    All your data will be removed from our system.
                    """)
            
                    if st.checkbox("I understand and want to proceed"):
                        if st.button("Permanently Delete My Account"):
                            deleted = services.user_delete_account(
                                username=st.session_state.username,
                                customer_id=cust_id
                            )
                            if deleted:
                                st.success("Account deleted successfully!")
                                logout_user()  # Automatically log out after deletion
                            else:
                                st.error("Account deletion failed")

st.markdown(
    """
    <hr>
    <p style='text-align: center; color: grey; font-size:18px;'>
    Made with ❤️ by <strong>ELITE CODERS</strong> <br>
    © 2025 All rights reserved.
    </p>
    """,
    unsafe_allow_html=True
)                          