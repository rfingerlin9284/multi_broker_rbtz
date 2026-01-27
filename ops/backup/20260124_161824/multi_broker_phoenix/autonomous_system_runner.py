"""Autonomous system runner that wires the hive agent to all brokers and data feeds.

This module ties together the pre-built connectors, AI hive agent, and integration
helpers so that running ``python -m multi_broker_phoenix.autonomous_system_runner``
spins up a single autonomous trading system that uses every enabled component.
"""

import logging
import os
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector_enhanced import IBKRConnector
from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
from multi_broker_phoenix.startup_autonomous_hive import startup_autonomous_hive_agent

logger = logging.getLogger(__name__)


class BrokerExecutionAdapter:
    """Normalize connector behavior so the quality engine can always call place_order."""

    def __init__(self, broker_name: str, connector: Any, *, default_notional: float = 500.0):
        self.broker_name = broker_name
        self.connector = connector
        self.default_notional = default_notional
        self.last_price: Dict[str, float] = {}

    def place_order(self, symbol: str, side: str, size: float, entry_price: float,
                    stop_loss: Optional[float], take_profit: Optional[float], strategy: Optional[str]) -> Dict[str, Any]:
        """Translate the quality engine order into connector-specific calls."""
        if size is None or size <= 0:
            size = self.default_notional
        size = float(size)

        entry_price = float(entry_price) if entry_price and entry_price > 0 else self._resolve_price(symbol)
        if not entry_price or entry_price <= 0:
            return {'success': False, 'error': 'Missing entry price'}

        symbol_for_broker = self._adapt_symbol(symbol)
        stop_loss = stop_loss or self._compute_default_stop(entry_price, side)
        take_profit = take_profit or self._compute_default_target(entry_price, side)

        units = max(size / entry_price, 0.0001)
        candidate = SimpleNamespace(
            symbol=symbol_for_broker,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_id=strategy
        )

        try:
            if self.broker_name == 'coinbase':
                method = self.connector.place_paper_order if getattr(self.connector, 'paper_mode', True) else self.connector.place_live_order
                return method(candidate, units)
            if self.broker_name == 'oanda':
                return self.connector.place_order(candidate, max(int(round(units)), 1))
            if self.broker_name == 'ibkr':
                shares = max(int(round(units)), 1)
                return self.connector.place_order(
                    symbol=symbol_for_broker,
                    side=side,
                    size=shares,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy=strategy
                )
        except Exception as exc:
            logger.error(f"❌ {self.broker_name.upper()} execution failed: {exc}")
            return {'success': False, 'error': str(exc)}

        return {'success': False, 'error': 'Unsupported broker adapter'}

    def get_price(self, symbol: str) -> Optional[float]:
        """Attempt to read the latest price from the connector."""
        price = self._resolve_price(symbol)
        if price:
            self.last_price[symbol] = price
        return price

    def _resolve_price(self, symbol: str) -> Optional[float]:
        """Try several price accessors exposed by the connectors."""
        broker_symbol = self._adapt_symbol(symbol)
        for attr in ('get_last_price', 'fetch_live_price', 'get_current_price', 'get_price'):
            if hasattr(self.connector, attr):
                try:
                    value = getattr(self.connector, attr)(broker_symbol)
                    if value:
                        return float(value)
                except Exception:
                    continue
        return self.last_price.get(symbol)

    def _adapt_symbol(self, symbol: str) -> str:
        if self.broker_name == 'oanda':
            return symbol.replace('-', '_')
        return symbol

    @staticmethod
    def _compute_default_stop(entry_price: float, side: str) -> float:
        delta = entry_price * 0.02
        return entry_price - delta if side.upper() == 'BUY' else entry_price + delta

    @staticmethod
    def _compute_default_target(entry_price: float, side: str) -> float:
        delta = entry_price * 0.03
        return entry_price + delta if side.upper() == 'BUY' else entry_price - delta


class MarketDataCollector:
    """Gather market snapshots from every enabled connector."""

    def __init__(self, adapters: Dict[str, BrokerExecutionAdapter], symbols: List[str]):
        self.adapters = adapters
        self.symbols = symbols
        self.latest_prices: Dict[str, float] = {}

    def collect(self) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {}
        timestamp = time.time()

        for symbol in self.symbols:
            symbol_entry: Dict[str, Any] = {
                'symbol': symbol,
                'timestamp': timestamp,
                'brokers': {}
            }
            best_price: Optional[float] = None

            for name, adapter in self.adapters.items():
                price = adapter.get_price(symbol)
                if not price:
                    continue
                symbol_entry['brokers'][name] = {
                    'price': price,
                    'history': self._collect_history(adapter, symbol),
                    'timestamp': timestamp
                }
                best_price = price if best_price is None else best_price

            if best_price:
                self.latest_prices[symbol] = best_price

            snapshot[symbol] = symbol_entry
        return snapshot

    def get_current_prices(self) -> Dict[str, float]:
        return dict(self.latest_prices)

    @staticmethod
    def _collect_history(adapter: BrokerExecutionAdapter, symbol: str) -> List[Any]:
        connector = adapter.connector
        if hasattr(connector, 'get_historical_data'):
            try:
                return connector.get_historical_data(adapter._adapt_symbol(symbol)) or []
            except Exception:
                return []
        return []


class AutonomousSystemOrchestrator:
    """Bootstraps the entire autonomous hive stack with live connectors."""

    def __init__(self, symbols: Optional[List[str]] = None, scan_interval: Optional[float] = None):
        self.symbols = symbols or self._default_symbols()
        self.scan_interval = float(scan_interval or os.getenv('HEADLESS_POLL_SECONDS', '60.0'))
        self.adapters = self._build_adapters()
        self.market_data = MarketDataCollector(self.adapters, self.symbols)
        self.startup_data = self._initialize_hive()
        self.integration = self.startup_data.get('integration') if self.startup_data else None

        if self.integration:
            self.integration.brokers.update(self.adapters)
            self.integration.autonomous_enabled = True

    def _default_symbols(self) -> List[str]:
        env_symbols = os.getenv('FEED_SYMBOLS') or 'BTC-USD,ETH-USD,EUR_USD,USD_JPY'
        return [s.strip() for s in env_symbols.split(',') if s.strip()]

    def _build_adapters(self) -> Dict[str, BrokerExecutionAdapter]:
        adapters: Dict[str, BrokerExecutionAdapter] = {}
        defaults = {
            'coinbase': float(os.getenv('AUTONOMOUS_DEFAULT_COINBASE_USD', '20.0')),
            'oanda': float(os.getenv('AUTONOMOUS_DEFAULT_OANDA_USD', '1000.0')),
            'ibkr': float(os.getenv('AUTONOMOUS_DEFAULT_IBKR_USD', '2000.0'))
        }

        try:
            coinbase = CoinbaseConnector(paper_mode=True)
            adapters['coinbase'] = BrokerExecutionAdapter('coinbase', coinbase, default_notional=defaults['coinbase'])
        except Exception as exc:
            logger.warning(f"⚠️  Coinbase connector unavailable: {exc}")

        try:
            oanda = OANDAConnector()
            adapters['oanda'] = BrokerExecutionAdapter('oanda', oanda, default_notional=defaults['oanda'])
        except Exception as exc:
            logger.warning(f"⚠️  OANDA connector unavailable: {exc}")

        try:
            ibkr = IBKRConnector(paper_mode=True)
            adapters['ibkr'] = BrokerExecutionAdapter('ibkr', ibkr, default_notional=defaults['ibkr'])
        except Exception as exc:
            logger.warning(f"⚠️  IBKR connector unavailable: {exc}")

        return adapters

    def _initialize_hive(self) -> Dict[str, Any]:
        result = startup_autonomous_hive_agent()
        if not result or result.get('status') != 'READY':
            logger.error('❌ Autonomous hive startup failed – check logs and env')
        return result or {}

    def run(self) -> None:
        if not self.integration:
            logger.error('❌ Cannot run autonomous system without integration layer')
            return

        logger.info('🚀 Autonomous system runner online. All connectors wired together.')
        iteration = 0

        try:
            while True:
                iteration += 1
                logger.info(f'--- ITERATION {iteration} ---')
                market_data = self.market_data.collect()
                current_prices = self.market_data.get_current_prices()
                results = self.integration.execute_autonomous_iteration(market_data, current_prices)
                logger.info(f"Iteration {iteration} results: {results.get('strategies_executed', [])}")
                time.sleep(self.scan_interval)
        except KeyboardInterrupt:
            logger.info('🛑 Autonomous run interrupted by user')
        except Exception as exc:
            logger.error(f'❌ Autonomous runner crashed: {exc}')


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    symbols = None
    env_symbols = os.getenv('FEED_SYMBOLS')
    if env_symbols:
        symbols = [s.strip() for s in env_symbols.split(',') if s.strip()]

    poll_secs = os.getenv('HEADLESS_POLL_SECONDS')
    scan_interval = None
    if poll_secs:
        try:
            scan_interval = float(poll_secs)
        except ValueError:
            logger.warning(f"Invalid HEADLESS_POLL_SECONDS value: {poll_secs}")

    orchestrator = AutonomousSystemOrchestrator(symbols=symbols, scan_interval=scan_interval)
    orchestrator.run()


if __name__ == '__main__':
    main()
