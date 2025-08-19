import os
import sys

# Set up absolute imports FIRST
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask
from flask_cors import CORS

# Now safe to import
from backend.razorpay_utils import save_keys, create_upi_order, check_payment_status
from backend.routes import routes
from backend.scheduler import start_scheduler

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    CORS(app)
    
    # Register the blueprint
    app.register_blueprint(routes, url_prefix='/api')
    
    return app

app = create_app()

if __name__ == "__main__":
    start_scheduler()
    app.run(debug=True, port=5000)