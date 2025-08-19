import os, csv
from functools import wraps
from datetime import datetime

LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'logs.csv')

def log_action(message=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            log_entry = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'function': func.__name__,
                'message': message or '',
                'args': str(args) if args else '',
                'kwargs': str(kwargs) if kwargs else ''
            }
            file_exists = os.path.isfile(LOG_FILE_PATH)
            with open(LOG_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=log_entry.keys())
                if not file_exists: writer.writeheader()
                writer.writerow(log_entry)
            return result
        return wrapper
    return decorator
