"""Market Sessions Module - Trading hours for major global exchanges

Defines trading session times for NYC, London, and Asian markets with
timezone-aware utilities for session detection and overlap analysis.
"""
from datetime import datetime, time
from typing import Optional, List, Dict, Tuple
import pytz


class MarketSession:
    """Represents a trading session with open/close times"""
    
    def __init__(self, name: str, timezone: str, open_time: time, close_time: time, 
                 days: Optional[List[int]] = None):
        """
        Args:
            name: Session name (e.g., 'NEW_YORK', 'LONDON', 'TOKYO')
            timezone: Timezone string (e.g., 'America/New_York')
            open_time: Session open time
            close_time: Session close time
            days: Trading days (0=Monday, 6=Sunday), defaults to Mon-Fri
        """
        self.name = name
        self.timezone = pytz.timezone(timezone)
        self.open_time = open_time
        self.close_time = close_time
        self.days = days if days is not None else [0, 1, 2, 3, 4]  # Mon-Fri
    
    def is_active(self, dt: Optional[datetime] = None) -> bool:
        """Check if session is currently active"""
        if dt is None:
            dt = datetime.now(pytz.UTC)
        
        # Convert to session timezone
        local_time = dt.astimezone(self.timezone)
        
        # Check if it's a trading day
        if local_time.weekday() not in self.days:
            return False
        
        current_time = local_time.time()
        
        # Handle sessions that cross midnight
        if self.close_time < self.open_time:
            return current_time >= self.open_time or current_time <= self.close_time
        else:
            return self.open_time <= current_time <= self.close_time
    
    def time_until_open(self, dt: Optional[datetime] = None) -> Optional[float]:
        """Returns seconds until session opens, None if already open"""
        if dt is None:
            dt = datetime.now(pytz.UTC)
        
        if self.is_active(dt):
            return None
        
        local_time = dt.astimezone(self.timezone)
        today = local_time.date()
        
        # Try today's open
        open_dt = self.timezone.localize(datetime.combine(today, self.open_time))
        if dt < open_dt:
            return (open_dt - dt).total_seconds()
        
        # Try tomorrow
        from datetime import timedelta
        tomorrow = today + timedelta(days=1)
        open_dt = self.timezone.localize(datetime.combine(tomorrow, self.open_time))
        return (open_dt - dt).total_seconds()
    
    def time_until_close(self, dt: Optional[datetime] = None) -> Optional[float]:
        """Returns seconds until session closes, None if not open"""
        if dt is None:
            dt = datetime.now(pytz.UTC)
        
        if not self.is_active(dt):
            return None
        
        local_time = dt.astimezone(self.timezone)
        today = local_time.date()
        
        close_dt = self.timezone.localize(datetime.combine(today, self.close_time))
        
        # Handle cross-midnight sessions
        if self.close_time < self.open_time and local_time.time() < self.close_time:
            # Currently in the "next day" portion
            return (close_dt - dt).total_seconds()
        elif close_dt < dt:
            # Close time already passed today, must be tomorrow
            from datetime import timedelta
            tomorrow = today + timedelta(days=1)
            close_dt = self.timezone.localize(datetime.combine(tomorrow, self.close_time))
        
        return (close_dt - dt).total_seconds()


# Define major market sessions
SESSIONS = {
    'NEW_YORK': MarketSession(
        name='NEW_YORK',
        timezone='America/New_York',
        open_time=time(9, 30),   # 9:30 AM EST
        close_time=time(16, 0),  # 4:00 PM EST
    ),
    
    'LONDON': MarketSession(
        name='LONDON',
        timezone='Europe/London',
        open_time=time(8, 0),    # 8:00 AM GMT
        close_time=time(16, 30), # 4:30 PM GMT
    ),
    
    'TOKYO': MarketSession(
        name='TOKYO',
        timezone='Asia/Tokyo',
        open_time=time(9, 0),    # 9:00 AM JST
        close_time=time(15, 0),  # 3:00 PM JST
    ),
    
    'SYDNEY': MarketSession(
        name='SYDNEY',
        timezone='Australia/Sydney',
        open_time=time(10, 0),   # 10:00 AM AEDT
        close_time=time(16, 0),  # 4:00 PM AEDT
    ),
    
    'HONG_KONG': MarketSession(
        name='HONG_KONG',
        timezone='Asia/Hong_Kong',
        open_time=time(9, 30),   # 9:30 AM HKT
        close_time=time(16, 0),  # 4:00 PM HKT
    ),
    
    # 24-hour markets (Crypto, Forex)
    'CRYPTO_24H': MarketSession(
        name='CRYPTO_24H',
        timezone='UTC',
        open_time=time(0, 0),
        close_time=time(23, 59),
        days=[0, 1, 2, 3, 4, 5, 6]  # 7 days
    ),
    
    'FOREX_24H': MarketSession(
        name='FOREX_24H',
        timezone='UTC',
        open_time=time(0, 0),
        close_time=time(23, 59),
        days=[0, 1, 2, 3, 4]  # Mon-Fri, closes weekend
    ),
}


def get_active_sessions(dt: Optional[datetime] = None) -> List[str]:
    """Get list of currently active session names"""
    return [name for name, session in SESSIONS.items() if session.is_active(dt)]


def is_session_overlap(dt: Optional[datetime] = None) -> bool:
    """Check if multiple major sessions are overlapping (high liquidity)"""
    active = get_active_sessions(dt)
    major_sessions = {'NEW_YORK', 'LONDON', 'TOKYO'}
    active_major = [s for s in active if s in major_sessions]
    return len(active_major) >= 2


def get_session_info(dt: Optional[datetime] = None) -> Dict[str, Dict]:
    """Get comprehensive info about all sessions"""
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    info = {}
    for name, session in SESSIONS.items():
        is_active = session.is_active(dt)
        info[name] = {
            'active': is_active,
            'timezone': str(session.timezone),
            'open': session.open_time.strftime('%H:%M'),
            'close': session.close_time.strftime('%H:%M'),
        }
        
        if is_active:
            info[name]['time_until_close'] = session.time_until_close(dt)
        else:
            info[name]['time_until_open'] = session.time_until_open(dt)
    
    return info


def get_primary_session(dt: Optional[datetime] = None) -> Optional[str]:
    """Get the primary session based on priority: NY > London > Tokyo > Others"""
    active = get_active_sessions(dt)
    
    priority = ['NEW_YORK', 'LONDON', 'TOKYO', 'HONG_KONG', 'SYDNEY']
    for session in priority:
        if session in active:
            return session
    
    # If no major session, return first active
    return active[0] if active else None


def format_session_status(dt: Optional[datetime] = None) -> str:
    """Format current session status as human-readable string"""
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    active = get_active_sessions(dt)
    overlap = is_session_overlap(dt)
    primary = get_primary_session(dt)
    
    lines = [
        f"Current Time (UTC): {dt.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Active Sessions: {', '.join(active) if active else 'NONE'}",
        f"Primary Session: {primary or 'NONE'}",
        f"Session Overlap: {'YES (High Liquidity)' if overlap else 'NO'}",
    ]
    
    return '\n'.join(lines)


# Session overlap periods (high liquidity, best trading times)
OVERLAP_PERIODS = {
    'LONDON_NYC': {
        'sessions': ['LONDON', 'NEW_YORK'],
        'description': 'London-New York overlap (highest volume)',
        'optimal_for': ['Forex majors', 'Gold', 'Oil'],
    },
    'TOKYO_LONDON': {
        'sessions': ['TOKYO', 'LONDON'],
        'description': 'Tokyo-London overlap',
        'optimal_for': ['Yen pairs', 'Asian stocks'],
    },
    'SYDNEY_TOKYO': {
        'sessions': ['SYDNEY', 'TOKYO'],
        'description': 'Sydney-Tokyo overlap',
        'optimal_for': ['AUD pairs', 'Asian markets'],
    },
}


def get_current_overlap(dt: Optional[datetime] = None) -> Optional[Dict]:
    """Get information about current session overlap if any"""
    active = set(get_active_sessions(dt))
    
    for period_name, period_info in OVERLAP_PERIODS.items():
        required = set(period_info['sessions'])
        if required.issubset(active):
            return {
                'name': period_name,
                **period_info,
                'active_sessions': list(active)
            }
    
    return None


# Utility for strategies
def should_trade_now(instrument: str, dt: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Determine if it's optimal time to trade given instrument
    
    Returns:
        (should_trade: bool, reason: str)
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    active = get_active_sessions(dt)
    
    # Crypto - always tradeable
    if any(x in instrument.upper() for x in ['BTC', 'ETH', 'CRYPTO']):
        return True, "Crypto markets 24/7"
    
    # Forex - check major sessions
    if any(x in instrument.upper() for x in ['USD', 'EUR', 'GBP', 'JPY', 'AUD']):
        if 'NEW_YORK' in active or 'LONDON' in active:
            return True, "Major forex session active"
        elif 'TOKYO' in active:
            return True, "Tokyo session active"
        else:
            return False, "All major forex sessions closed"
    
    # US Stocks
    if 'NEW_YORK' in active:
        return True, "US market hours"
    
    # Default - check if any major session is active
    if active:
        return True, f"Trading during {', '.join(active)}"
    
    return False, "All markets closed"


if __name__ == '__main__':
    print("=" * 60)
    print("MARKET SESSIONS - Current Status")
    print("=" * 60)
    print()
    print(format_session_status())
    print()
    
    overlap = get_current_overlap()
    if overlap:
        print("=" * 60)
        print(f"OVERLAP DETECTED: {overlap['name']}")
        print("=" * 60)
        print(f"Description: {overlap['description']}")
        print(f"Optimal for: {', '.join(overlap['optimal_for'])}")
        print()
    
    # Test instruments
    test_instruments = ['BTC-USD', 'EUR_USD', 'SPY', 'ETH-USD']
    print("=" * 60)
    print("TRADING RECOMMENDATIONS")
    print("=" * 60)
    for instrument in test_instruments:
        should_trade, reason = should_trade_now(instrument)
        status = "✓ TRADE" if should_trade else "✗ WAIT"
        print(f"{status} {instrument:15s} - {reason}")
