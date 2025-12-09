from datetime import datetime, timedelta
import re

from dateutil.relativedelta import relativedelta

def parseRelDatetime(s: str) -> str:
    now = datetime.now()
    s = s.lower().strip()
    
    match = re.search(r"\d+", s)
    if not match:
        return s

    number = int(match.group())
        
    if "last minute" in s:
        dt = (now - timedelta(minutes=1)).replace(second=0, microsecond=0)
    elif "last hour" in s:
        dt = (now - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    elif "yesterday" in s:
        dt = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif "last month" in s:
        dt = (now - relativedelta(months=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif "last year" in s:
        dt = (now - relativedelta(years=1)).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    elif "minute" in s:
        dt = (now - timedelta(minutes=number)).replace(second=0, microsecond=0)
    elif "hour" in s:
        dt = (now - timedelta(hours=number)).replace(minute=0, second=0, microsecond=0)
    elif "day" in s:
        dt = (now - timedelta(days=number)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif "month" in s:
        dt = (now - relativedelta(months=number)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif "year" in s:
        dt = (now - relativedelta(years=number)).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return s

    return dt.strftime("%Y-%m-%d %H:%M:%S")
