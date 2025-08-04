from datetime import datetime

def timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to readable datetime format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")