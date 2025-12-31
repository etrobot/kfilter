"""Market data processing modules"""

def __getattr__(name):
    """Lazy import to avoid loading unavailable dependencies"""
    if name == 'fetch_hot_spot':
        from utils.quotation import fetch_hot_spot
        return fetch_hot_spot
    elif name == 'fetch_history':
        from .data_fetcher import fetch_history
        return fetch_history
    elif name == 'fetch_dragon_tiger_data':
        from .data_fetcher import fetch_dragon_tiger_data
        return fetch_dragon_tiger_data
    elif name == 'compute_factors':
        from .data_fetcher import compute_factors
        return compute_factors
    elif name == 'calculate_and_save_weekly_data':
        from .kline_processor import calculate_and_save_weekly_data
        return calculate_and_save_weekly_data
    elif name == 'calculate_and_save_monthly_data':
        from .kline_processor import calculate_and_save_monthly_data
        return calculate_and_save_monthly_data
    elif name == 'get_weekly_data':
        from .kline_processor import get_weekly_data
        return get_weekly_data
    elif name == 'get_monthly_data':
        from .kline_processor import get_monthly_data
        return get_monthly_data
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'fetch_hot_spot',
    'fetch_history',
    'fetch_dragon_tiger_data',
    'compute_factors',
    'calculate_and_save_weekly_data',
    'calculate_and_save_monthly_data',
    'get_weekly_data',
    'get_monthly_data'
]