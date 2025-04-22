from datetime import datetime, timezone
import pytz

def utc_to_timezone(dt: datetime, tz_name: str = 'Africa/Cairo') -> datetime:
    """
    Convert a UTC datetime to a specific timezone
    
    Args:
        dt: The UTC datetime to convert
        tz_name: The timezone name (default: 'Africa/Cairo' for Egypt)
        
    Returns:
        The datetime in the specified timezone
    """
    if dt is None:
        return None
        
    # Ensure the datetime is timezone-aware and in UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    
    # Convert to the target timezone
    target_tz = pytz.timezone(tz_name)
    return dt.astimezone(target_tz)

def format_datetime(dt: datetime, tz_name: str = 'Africa/Cairo', fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format a datetime in a specific timezone
    
    Args:
        dt: The datetime to format (assumed to be in UTC if no timezone)
        tz_name: The timezone name (default: 'Africa/Cairo' for Egypt)
        fmt: The format string (default: '%Y-%m-%d %H:%M:%S')
        
    Returns:
        The formatted datetime string
    """
    if dt is None:
        return None
        
    # Convert to the target timezone
    dt_in_tz = utc_to_timezone(dt, tz_name)
    
    # Format the datetime
    return dt_in_tz.strftime(fmt)
