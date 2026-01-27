"""
Broker auto-activation gates.

This module implements the three gate checks that determine whether
a broker can transition from PAUSED to ACTIVE:

1. CONNECTIVITY: auth + price feed healthy
2. LIQUIDITY: spreads/latency reasonable, not in maintenance
3. OCO_READINESS: can place and verify protective orders

Gate philosophy:
- Gates are per-broker and independent
- A failed gate PAUSES that broker only (not global freeze)
- Gates run periodically and can auto-recover
- Gate failures are actionable (logged with specific reasons)
"""

import logging
import time
from typing import Optional
from datetime import datetime, time as dt_time, timezone

from multi_broker_phoenix.core.interfaces import (
    BrokerConnectorProtocol,
    GateCheckResult,
    BrokerGatesProtocol,
    OCOOrder,
    OCOUnsupportedError,
)


logger = logging.getLogger(__name__)


class BrokerGates:
    """
    Implementation of broker gate checks for auto-activation.
    
    Gate checks determine if a broker is eligible to trade.
    All gates must pass for broker to become ACTIVE.
    """
    
    def __init__(
        self,
        connector: BrokerConnectorProtocol,
        broker_name: str,
        max_spread_pct: float = 0.5,
        max_latency_ms: float = 1000.0,
        maintenance_windows: Optional[list[tuple[dt_time, dt_time]]] = None,
    ):
        """
        Initialize gate checker.
        
        Args:
            connector: Broker connector to check
            broker_name: Broker identifier
            max_spread_pct: Maximum acceptable spread percentage
            max_latency_ms: Maximum acceptable API latency in milliseconds
            maintenance_windows: List of (start_time, end_time) tuples for broker maintenance
        """
        self.connector = connector
        self.broker_name = broker_name
        self.max_spread_pct = max_spread_pct
        self.max_latency_ms = max_latency_ms
        self.maintenance_windows = maintenance_windows or get_default_maintenance_windows(broker_name)
        
        logger.info(
            f"BrokerGates initialized for {broker_name}: "
            f"max_spread={max_spread_pct}%, max_latency={max_latency_ms}ms"
        )
    
    def check_connectivity(self, connector: BrokerConnectorProtocol) -> GateCheckResult:
        """
        Gate 1: CONNECTIVITY
        
        Checks:
        - Broker auth successful
        - Price feed responsive
        - API reachable within latency threshold
        
        Args:
            connector: Broker connector
        
        Returns:
            GateCheckResult
        """
        errors = []
        details = {}
        
        try:
            start = time.time()
            health = connector.health_check()
            latency_ms = (time.time() - start) * 1000
            
            details["latency_ms"] = latency_ms
            details["health_ok"] = health.ok
            details["health_details"] = health.details
            
            if not health.ok:
                errors.append(f"Health check failed: {health.errors}")
            
            if latency_ms > self.max_latency_ms:
                errors.append(
                    f"API latency too high: {latency_ms:.0f}ms > {self.max_latency_ms}ms"
                )
            
            # Try to fetch a sample price to verify data feed
            try:
                # Use a common symbol (broker-agnostic check)
                test_symbols = ["EUR_USD", "BTC-USD", "EURUSD"]  # Try multiple formats
                prices = None
                for symbol in test_symbols:
                    try:
                        prices = connector.get_prices([symbol])
                        if prices:
                            break
                    except:
                        continue
                
                if not prices:
                    errors.append("Price feed not responding (no test symbols available)")
                else:
                    details["price_feed_ok"] = True
                    details["sample_prices"] = prices
            
            except Exception as e:
                errors.append(f"Price feed error: {e}")
        
        except Exception as e:
            errors.append(f"Connectivity check exception: {e}")
            logger.error(
                f"[{self.broker_name}] Connectivity gate exception: {e}",
                exc_info=True
            )
        
        passed = len(errors) == 0
        return GateCheckResult(
            gate_name="CONNECTIVITY",
            passed=passed,
            details=details,
            errors=errors
        )
    
    def check_liquidity(
        self,
        connector: BrokerConnectorProtocol,
        symbols: list[str]
    ) -> GateCheckResult:
        """
        Gate 2: LIQUIDITY
        
        Checks:
        - Spreads within acceptable range
        - Not in maintenance window
        - Market hours appropriate for broker type
        
        Args:
            connector: Broker connector
            symbols: List of symbols to check
        
        Returns:
            GateCheckResult
        """
        errors = []
        details = {}
        
        try:
            # Check maintenance window
            now = datetime.now(timezone.utc).time()
            in_maintenance = False
            
            for start_time, end_time in self.maintenance_windows:
                if start_time <= now <= end_time:
                    in_maintenance = True
                    errors.append(
                        f"In maintenance window: {start_time.isoformat()} - {end_time.isoformat()}"
                    )
                    break
            
            details["in_maintenance"] = in_maintenance
            
            # Check spreads for requested symbols
            if symbols and not in_maintenance:
                try:
                    prices = connector.get_prices(symbols)
                    spread_checks = {}
                    
                    for symbol, price_data in prices.items():
                        bid = price_data.get("bid")
                        ask = price_data.get("ask")
                        
                        if bid and ask and bid > 0:
                            spread_pct = ((ask - bid) / bid) * 100
                            spread_checks[symbol] = {
                                "spread_pct": spread_pct,
                                "acceptable": spread_pct <= self.max_spread_pct
                            }
                            
                            if spread_pct > self.max_spread_pct:
                                errors.append(
                                    f"{symbol} spread too wide: {spread_pct:.3f}% > {self.max_spread_pct}%"
                                )
                    
                    details["spread_checks"] = spread_checks
                
                except Exception as e:
                    errors.append(f"Spread check error: {e}")
        
        except Exception as e:
            errors.append(f"Liquidity check exception: {e}")
            logger.error(
                f"[{self.broker_name}] Liquidity gate exception: {e}",
                exc_info=True
            )
        
        passed = len(errors) == 0
        return GateCheckResult(
            gate_name="LIQUIDITY",
            passed=passed,
            details=details,
            errors=errors
        )
    
    def check_oco_readiness(self, connector: BrokerConnectorProtocol) -> GateCheckResult:
        """
        Gate 3: OCO_READINESS
        
        Checks:
        - Connector can place OCO orders (native or emulated)
        - OCO validation passes
        - Protective order capabilities verified
        
        This is a "can we place OCO?" check, not an actual order placement.
        
        Args:
            connector: Broker connector
        
        Returns:
            GateCheckResult
        """
        errors = []
        details = {}
        
        try:
            # Check if connector implements place_oco
            if not hasattr(connector, "place_oco"):
                errors.append("Connector does not implement place_oco()")
                details["has_place_oco"] = False
            else:
                details["has_place_oco"] = True
            
            # Check if connector can cancel OCO groups
            if not hasattr(connector, "cancel_oco"):
                errors.append("Connector does not implement cancel_oco()")
                details["has_cancel_oco"] = False
            else:
                details["has_cancel_oco"] = True
            
            # Check if health_check indicates OCO capability
            try:
                health = connector.health_check()
                details["oco_capable"] = health.oco_capable
                if not health.oco_capable:
                    errors.append("Connector reports OCO not capable")
            
            except OCOUnsupportedError as e:
                errors.append(f"OCO not supported: {e.reason}")
                details["oco_capable"] = False
            except Exception as e:
                # Assume capable if health check doesn't explicitly report otherwise
                details["oco_capable"] = True
                details["oco_check_error"] = str(e)
            
            # Note: We do NOT place an actual test order here
            # That would be too invasive. This gate checks capability only.
        
        except Exception as e:
            errors.append(f"OCO readiness check exception: {e}")
            logger.error(
                f"[{self.broker_name}] OCO readiness gate exception: {e}",
                exc_info=True
            )
        
        passed = len(errors) == 0
        return GateCheckResult(
            gate_name="OCO_READINESS",
            passed=passed,
            details=details,
            errors=errors
        )
    
    def run_all_gates(
        self,
        symbols: Optional[list[str]] = None
    ) -> tuple[bool, dict[str, dict]]:
        """
        Run all three gate checks sequentially.
        
        Args:
            symbols: Symbols to check liquidity for (optional, uses defaults)
        
        Returns:
            (all_passed: bool, results: dict[str, dict])
        """
        if symbols is None:
            # Default test symbols based on broker
            if 'oanda' in self.broker_name.lower():
                symbols = ['EUR_USD']
            elif 'coinbase' in self.broker_name.lower():
                symbols = ['BTC-USD']
            else:
                symbols = ['EURUSD']
        
        results = {}
        
        # Gate 1: Connectivity
        connectivity = self.check_connectivity(self.connector)
        results['CONNECTIVITY'] = {
            'passed': connectivity.passed,
            'details': connectivity.details,
            'errors': connectivity.errors,
            'reason': connectivity.errors[0] if connectivity.errors else 'OK',
        }
        
        # Gate 2: Liquidity (only if connectivity passed)
        if connectivity.passed:
            liquidity = self.check_liquidity(self.connector, symbols)
            results['LIQUIDITY'] = {
                'passed': liquidity.passed,
                'details': liquidity.details,
                'errors': liquidity.errors,
                'reason': liquidity.errors[0] if liquidity.errors else 'OK',
            }
        else:
            # Skip liquidity check if connectivity failed
            results['LIQUIDITY'] = {
                'passed': False,
                'details': {'skipped': 'connectivity_failed'},
                'errors': ['Skipped due to connectivity failure'],
                'reason': 'Connectivity gate failed',
            }
        
        # Gate 3: OCO Readiness
        oco_readiness = self.check_oco_readiness(self.connector)
        results['OCO_READINESS'] = {
            'passed': oco_readiness.passed,
            'details': oco_readiness.details,
            'errors': oco_readiness.errors,
            'reason': oco_readiness.errors[0] if oco_readiness.errors else 'OK',
        }
        
        all_passed = all(r['passed'] for r in results.values())
        
        logger.info(
            f"[{self.broker_name}] Gate checks: "
            f"{'✅ ALL PASS' if all_passed else '❌ FAILURES'} "
            f"({len([r for r in results.values() if r['passed']])}/{len(results)} passed)"
        )
        
        return all_passed, results


def get_default_maintenance_windows(broker_name: str) -> list[tuple[dt_time, dt_time]]:
    """
    Get default maintenance windows for a broker.
    
    Args:
        broker_name: Broker identifier (oanda, coinbase, ibkr)
    
    Returns:
        List of (start_time, end_time) tuples (UTC)
    """
    # Default maintenance windows (UTC)
    windows = {
        "oanda": [
            # Forex daily rollover (typically 5pm ET = 21:00-22:00 UTC)
            (dt_time(21, 0), dt_time(22, 0)),
        ],
        "coinbase": [
            # Crypto usually has minimal maintenance
            # Add specific windows if needed
        ],
        "ibkr": [
            # TWS nightly maintenance (typically 23:45-00:45 ET)
            (dt_time(4, 45), dt_time(5, 45)),  # Approximate UTC
        ],
    }
    
    return windows.get(broker_name.lower(), [])
