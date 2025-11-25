"""
Utility functions for the task management application.
"""
from datetime import date, timedelta

def calculate_business_days_until(target_date):
    """
    Calculate the number of business days (Monday-Friday) from today until target_date.
    
    Args:
        target_date: datetime.date or datetime.datetime object
        
    Returns:
        int: Number of business days until target_date (0 if target is today or in the past)
    """
    # Convert datetime to date if necessary
    if hasattr(target_date, 'date'):
        target_date = target_date.date()
    
    today = date.today()
    
    # If target is today or in the past, return 0
    if target_date <= today:
        return 0
    
    business_days = 0
    current_date = today
    
    # Count business days until target
    while current_date < target_date:
        current_date += timedelta(days=1)
        # 0 = Monday, 6 = Sunday
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
    
    return business_days

def is_business_day(check_date):
    """
    Check if a given date is a business day (Monday-Friday).
    
    Args:
        check_date: datetime.date or datetime.datetime object
        
    Returns:
        bool: True if it's a business day, False otherwise
    """
    # Convert datetime to date if necessary
    if hasattr(check_date, 'date'):
        check_date = check_date.date()
    
    # 0-4 = Monday-Friday, 5-6 = Saturday-Sunday
    return check_date.weekday() < 5
