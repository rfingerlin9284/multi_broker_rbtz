"""
Market Session Awareness
Determines which markets are open based on current time
"""
from datetime import datetime, timezone
from typing import Dict, List, Set
from enum import Enum
import pytz

class MarketType(Enum):
    FOREX = "forex"
    CRYPTO = "crypto"
    EQUITY_FUTURES = "equity_futures"
    COMMODITY_FUTURES = "commodity_futures"

class MarketSession:
    """Determines which markets are currently tradeable."""
    
    def __init__(self):
        self.chicago_tz = pytz.timezone('America/Chicago')
        self.utc_tz = pytz.UTC
        
    def get_current_time_info(self) -> Dict:
        """Get comprehensive time information."""
        now_utc = datetime.now(self.utc_tz)
        now_chicago = now_utc.astimezone(self.chicago_tz)
        
        # Day of week (0=Monday, 6=Sunday)
        weekday = now_utc.weekday()
        is_weekend = weekday >= 5  # Saturday or Sunday
        
        return {
            'utc': now_utc,
            'chicago': now_chicago,
            'chicago_hour': now_chicago.hour,
            'weekday': weekday,
            'is_weekend': is_weekend,
            'day_name': now_chicago.strftime('%A')
        }
    
    def is_forex_open(self) -> bool:
        """Check if forex market is open (Sunday 5pm CT - Friday 5pm CT)."""
        time_info = self.get_current_time_info()
        chicago_hour = time_info['chicago_hour']
        weekday = time_info['weekday']
        
        # Forex closes Friday 5pm CT, reopens Sunday 5pm CT
        if weekday == 4:  # Friday
            return chicago_hour < 17
        elif weekday == 5:  # Saturday
            return False
        elif weekday == 6:  # Sunday
            return chicago_hour >= 17
        else:  # Monday-Thursday
            return True
    
    def is_crypto_open(self) -> bool:
        """Crypto markets are always open."""
        return True
    
    def is_futures_open(self) -> bool:
        """Check if futures are in trading hours.
        
        Most futures: Sunday 6pm CT - Friday 5pm CT
        Nearly 24-hour with brief maintenance 5-6pm CT daily
        """
        time_info = self.get_current_time_info()
        chicago_hour = time_info['chicago_hour']
        weekday = time_info['weekday']
        
        # Maintenance window daily 5-6pm CT
        if chicago_hour == 17:  # 5pm hour
            return False
        
        # Friday close at 5pm CT
        if weekday == 4 and chicago_hour >= 17:
            return False
        
        # Saturday closed
        if weekday == 5:
            return False
        
        # Sunday open from 6pm CT
        if weekday == 6:
            return chicago_hour >= 18
        
        # Monday-Thursday open except maintenance
        return True
    
    def get_open_markets(self) -> Dict[str, bool]:
        """Get status of all markets."""
        return {
            'forex': self.is_forex_open(),
            'crypto': self.is_crypto_open(),
            'equity_futures': self.is_futures_open(),
            'commodity_futures': self.is_futures_open()
        }
    
    def filter_symbols_by_session(self, symbols: List[str]) -> List[str]:
        """Filter symbol list to only tradeable markets."""
        open_markets = self.get_open_markets()
        tradeable = []
        
        for symbol in symbols:
            # Crypto (contains USD, BTC, ETH but not underscore)
            if '-USD' in symbol or 'BTC' in symbol or 'ETH' in symbol:
                if open_markets['crypto']:
                    tradeable.append(symbol)
            
            # Forex (contains underscore - EUR_USD, GBP_USD, etc)
            elif '_' in symbol:
                if open_markets['forex']:
                    tradeable.append(symbol)
            
            # Futures (2-letter codes or CME style)
            elif len(symbol) <= 3 or symbol in ['ES', 'NQ', 'CL', 'GC', '6E', '6J', 'ZN', 'ZB']:
                if open_markets['commodity_futures']:
                    tradeable.append(symbol)
            
            # Default to including if unsure
            else:
                tradeable.append(symbol)
        
        return tradeable
    
    def get_session_status_display(self) -> str:
        """Get formatted display of current market status."""
        time_info = self.get_current_time_info()
        open_markets = self.get_open_markets()
        
        chicago_time = time_info['chicago'].strftime('%I:%M %p %Z')
        day_name = time_info['day_name']
        
        status = f"""
╔════════════════════════════════════════════════════════════════╗
║  MARKET SESSION STATUS                                         ║
╠════════════════════════════════════════════════════════════════╣
║  Current Time: {day_name} {chicago_time:<40} ║
╠════════════════════════════════════════════════════════════════╣
"""
        
        # Forex
        forex_status = "🟢 OPEN" if open_markets['forex'] else "🔴 CLOSED"
        status += f"║  📊 FOREX (EUR_USD, GBP_USD, etc):      {forex_status:<22} ║\n"
        
        # Crypto
        crypto_status = "🟢 OPEN" if open_markets['crypto'] else "🔴 CLOSED"
        status += f"║  ₿  CRYPTO (BTC-USD, ETH-USD):          {crypto_status:<22} ║\n"
        
        # Futures
        futures_status = "🟢 OPEN" if open_markets['equity_futures'] else "🔴 CLOSED"
        status += f"║  📈 FUTURES (ES, CL, GC, 6E):           {futures_status:<22} ║\n"
        
        status += "╚════════════════════════════════════════════════════════════════╝\n"
        
        # Trading hours info
        if not open_markets['forex']:
            status += "\n⏰ FOREX: Opens Sunday 5:00 PM CT / Closes Friday 5:00 PM CT"
        if not open_markets['commodity_futures']:
            status += "\n⏰ FUTURES: Opens Sunday 6:00 PM CT / Brief maintenance daily 5-6 PM CT"
        
        return status
    
    def get_tradeable_instruments_count(self, all_symbols: List[str]) -> Dict:
        """Count how many instruments are currently tradeable."""
        tradeable = self.filter_symbols_by_session(all_symbols)
        open_markets = self.get_open_markets()
        
        forex_count = sum(1 for s in tradeable if '_' in s)
        crypto_count = sum(1 for s in tradeable if '-USD' in s or 'BTC' in s or 'ETH' in s)
        futures_count = len(tradeable) - forex_count - crypto_count
        
        return {
            'total': len(tradeable),
            'forex': forex_count,
            'crypto': crypto_count,
            'futures': futures_count,
            'tradeable_symbols': tradeable,
            'open_markets': open_markets
        }
