"""Unit tests for the "Never Again $300 Surprise" Safety Pack.

Run with: python -m unittest tests/test_safety_pack.py -v

Tests:
1. test_pip_value_eurusd: Verifies pip value math for EUR_USD
2. test_risk_to_sl_usd: Verifies 30 pips at ~106k units ≈ ~$320
3. test_pretrade_risk_veto: Engine refuses order if SL implies > MAX_RISK_USD_PER_TRADE
4. test_reconcile_detects_missing_oco: Simulate broker returning open trade without SL/TP
5. test_repair_fail_emergency_flatten: If repair fails and risk exceeds threshold, flatten
"""
import unittest
import os
import sys
import time

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class TestPipMath(unittest.TestCase):
    """Test pip→$ conversion math."""
    
    def test_pip_size_standard(self):
        """Test pip size for standard pairs."""
        from multi_broker_phoenix.risk.pip_math import pip_size
        
        # Standard pairs: 0.0001
        self.assertEqual(pip_size('EUR_USD'), 0.0001)
        self.assertEqual(pip_size('GBP_USD'), 0.0001)
        self.assertEqual(pip_size('AUD_USD'), 0.0001)
        self.assertEqual(pip_size('USD_CAD'), 0.0001)
        self.assertEqual(pip_size('EUR/USD'), 0.0001)  # Alternate format
    
    def test_pip_size_jpy(self):
        """Test pip size for JPY pairs."""
        from multi_broker_phoenix.risk.pip_math import pip_size
        
        # JPY pairs: 0.01
        self.assertEqual(pip_size('USD_JPY'), 0.01)
        self.assertEqual(pip_size('EUR_JPY'), 0.01)
        self.assertEqual(pip_size('GBP_JPY'), 0.01)
    
    def test_pip_value_eurusd(self):
        """Test pip value for EUR_USD.
        
        Acceptance: Given units=106,765 on EUR_USD, pip value ≈ ~10.67 USD/pip
        """
        from multi_broker_phoenix.risk.pip_math import pip_value_usd
        
        units = 106765
        pair = 'EUR_USD'
        price = 1.1200
        
        pv = pip_value_usd(units, pair, price)
        
        # Expected: 106765 * 0.0001 = 10.6765
        self.assertAlmostEqual(pv, 10.6765, places=4)
        # Accept range 10.5 - 10.8
        self.assertGreater(pv, 10.5)
        self.assertLess(pv, 10.8)
    
    def test_pip_value_usdjpy(self):
        """Test pip value for USD_JPY (inverted pair)."""
        from multi_broker_phoenix.risk.pip_math import pip_value_usd
        
        units = 100000
        pair = 'USD_JPY'
        price = 150.00  # Typical USD/JPY rate
        
        pv = pip_value_usd(units, pair, price)
        
        # Expected: (100000 * 0.01) / 150 = 1000 / 150 ≈ 6.67
        self.assertAlmostEqual(pv, 6.67, places=1)
    
    def test_risk_to_sl_usd_30_pips(self):
        """Test risk to SL calculation.
        
        Acceptance: 30 pips at ~106k units ≈ ~$320
        """
        from multi_broker_phoenix.risk.pip_math import risk_to_sl_usd, sl_distance_pips
        
        units = 106765
        pair = 'EUR_USD'
        entry = 1.1200
        sl = 1.1170  # 30 pips
        
        # Verify pip distance
        pips = sl_distance_pips(entry, sl, pair)
        self.assertAlmostEqual(pips, 30.0, places=0)
        
        # Verify risk in USD
        risk = risk_to_sl_usd(units, pair, entry, sl)
        
        # Expected: 30 pips * 10.6765 USD/pip ≈ $320.30
        self.assertAlmostEqual(risk, 320.30, places=0)
        # Accept range $310 - $330
        self.assertGreater(risk, 310)
        self.assertLess(risk, 330)
    
    def test_compute_risk_metrics(self):
        """Test comprehensive risk metrics computation."""
        from multi_broker_phoenix.risk.pip_math import compute_risk_metrics, calculate_rr_ratio
        
        units = 10000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.0980  # 20 pips
        tp = 1.1040  # 40 pips (2:1 RR)
        
        metrics = compute_risk_metrics(units, pair, entry, sl, tp)
        
        self.assertEqual(metrics['units'], 10000)
        self.assertEqual(metrics['pair'], pair)
        self.assertEqual(metrics['pip_size'], 0.0001)
        self.assertAlmostEqual(metrics['pip_value_usd'], 1.0, places=2)
        self.assertAlmostEqual(metrics['sl_distance_pips'], 20.0, places=0)
        self.assertAlmostEqual(metrics['tp_distance_pips'], 40.0, places=0)
        self.assertAlmostEqual(metrics['risk_to_sl_usd'], 20.0, places=0)
        self.assertAlmostEqual(metrics['reward_to_tp_usd'], 40.0, places=0)
        self.assertAlmostEqual(metrics['rr_ratio'], 2.0, places=1)


class TestRiskGovernor(unittest.TestCase):
    """Test pre-trade risk validation."""
    
    def test_pretrade_risk_veto(self):
        """Test that engine refuses order if SL implies > MAX_RISK_USD_PER_TRADE."""
        from multi_broker_phoenix.risk.pip_math import validate_trade_risk
        
        # Create a trade that exceeds risk budget
        units = 100000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.0950  # 50 pips = $500 risk
        tp = 1.1100  # 100 pips (2:1 RR)
        
        # With MAX_RISK = $25, this should be VETOED
        config = {
            'MAX_RISK_USD_PER_TRADE': 25.0,
            'MIN_RR': 1.0,
            'MAX_UNITS_PER_PAIR': 1000000,
        }
        
        result = validate_trade_risk(units, pair, entry, sl, tp, 'BUY', config)
        
        self.assertFalse(result['allowed'])
        self.assertTrue(any('RISK_EXCEED_MAX' in v for v in result['violations']))
        self.assertIsNotNone(result['suggested_units'])
        # Suggested units should be much smaller
        self.assertLess(result['suggested_units'], units)
    
    def test_pretrade_risk_pass(self):
        """Test that small risk trade passes validation."""
        from multi_broker_phoenix.risk.pip_math import validate_trade_risk
        
        # Small trade within budget
        units = 1000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.0980  # 20 pips = $2 risk
        tp = 1.1040  # 40 pips (2:1 RR)
        
        config = {
            'MAX_RISK_USD_PER_TRADE': 25.0,
            'MIN_RR': 1.5,
            'MAX_UNITS_PER_PAIR': 100000,
        }
        
        result = validate_trade_risk(units, pair, entry, sl, tp, 'BUY', config)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(len(result['violations']), 0)
    
    def test_pretrade_rr_veto(self):
        """Test that low RR trade is vetoed."""
        from multi_broker_phoenix.risk.pip_math import validate_trade_risk
        
        units = 1000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.0980  # 20 pips
        tp = 1.1010  # 10 pips (0.5:1 RR - bad!)
        
        config = {
            'MAX_RISK_USD_PER_TRADE': 100.0,
            'MIN_RR': 1.5,
            'MAX_UNITS_PER_PAIR': 100000,
        }
        
        result = validate_trade_risk(units, pair, entry, sl, tp, 'BUY', config)
        
        self.assertFalse(result['allowed'])
        self.assertTrue(any('RR_BELOW_MIN' in v for v in result['violations']))
    
    def test_sl_wrong_direction_buy(self):
        """Test that BUY with SL above entry is vetoed."""
        from multi_broker_phoenix.risk.pip_math import validate_trade_risk
        
        units = 1000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.1020  # SL above entry for BUY - WRONG!
        tp = 1.1040
        
        result = validate_trade_risk(units, pair, entry, sl, tp, 'BUY')
        
        self.assertFalse(result['allowed'])
        self.assertTrue(any('SL_ABOVE_ENTRY' in v for v in result['violations']))
    
    def test_sl_wrong_direction_sell(self):
        """Test that SELL with SL below entry is vetoed."""
        from multi_broker_phoenix.risk.pip_math import validate_trade_risk
        
        units = 1000
        pair = 'EUR_USD'
        entry = 1.1000
        sl = 1.0980  # SL below entry for SELL - WRONG!
        tp = 1.0960
        
        result = validate_trade_risk(units, pair, entry, sl, tp, 'SELL')
        
        self.assertFalse(result['allowed'])
        self.assertTrue(any('SL_BELOW_ENTRY' in v for v in result['violations']))


class TestOCOReconcile(unittest.TestCase):
    """Test OCO reconciliation logic."""
    
    def test_validate_oco_ok(self):
        """Test that trade with valid SL+TP is marked OK."""
        from multi_broker_phoenix.risk.oco_reconcile import _validate_oco, _extract_trade_info
        
        trade = {
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',
            'price': '1.1000',
            'stopLoss': {'price': '1.0980'},
            'takeProfit': {'price': '1.1040'},
        }
        
        trade_info = _extract_trade_info(trade)
        result = _validate_oco(trade_info)
        
        self.assertEqual(result['status'], 'OK')
        self.assertTrue(result['has_sl'])
        self.assertTrue(result['has_tp'])
        self.assertTrue(result['sl_valid'])
        self.assertTrue(result['tp_valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_validate_oco_missing_sl(self):
        """Test detection of missing SL."""
        from multi_broker_phoenix.risk.oco_reconcile import _validate_oco, _extract_trade_info
        
        trade = {
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',
            'price': '1.1000',
            'takeProfit': {'price': '1.1040'},
            # No stopLoss!
        }
        
        trade_info = _extract_trade_info(trade)
        result = _validate_oco(trade_info)
        
        self.assertEqual(result['status'], 'MISSING')
        self.assertFalse(result['has_sl'])
        self.assertTrue(result['has_tp'])
        self.assertIn('MISSING_SL', result['issues'])
    
    def test_validate_oco_missing_tp(self):
        """Test detection of missing TP."""
        from multi_broker_phoenix.risk.oco_reconcile import _validate_oco, _extract_trade_info
        
        trade = {
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',
            'price': '1.1000',
            'stopLoss': {'price': '1.0980'},
            # No takeProfit!
        }
        
        trade_info = _extract_trade_info(trade)
        result = _validate_oco(trade_info)
        
        self.assertEqual(result['status'], 'MISSING')
        self.assertTrue(result['has_sl'])
        self.assertFalse(result['has_tp'])
        self.assertIn('MISSING_TP', result['issues'])
    
    def test_validate_oco_missing_both(self):
        """Test detection of missing both SL and TP."""
        from multi_broker_phoenix.risk.oco_reconcile import _validate_oco, _extract_trade_info
        
        trade = {
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',
            'price': '1.1000',
            # No stopLoss or takeProfit!
        }
        
        trade_info = _extract_trade_info(trade)
        result = _validate_oco(trade_info)
        
        self.assertEqual(result['status'], 'MISSING')
        self.assertFalse(result['has_sl'])
        self.assertFalse(result['has_tp'])
        self.assertIn('MISSING_SL', result['issues'])
        self.assertIn('MISSING_TP', result['issues'])
    
    def test_validate_oco_invalid_sl_direction(self):
        """Test detection of SL in wrong direction for BUY."""
        from multi_broker_phoenix.risk.oco_reconcile import _validate_oco, _extract_trade_info
        
        trade = {
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',  # Positive = BUY
            'price': '1.1000',
            'stopLoss': {'price': '1.1020'},  # SL above entry for BUY - WRONG!
            'takeProfit': {'price': '1.1040'},
        }
        
        trade_info = _extract_trade_info(trade)
        result = _validate_oco(trade_info)
        
        self.assertEqual(result['status'], 'INVALID')
        self.assertTrue(result['has_sl'])
        self.assertFalse(result['sl_valid'])
        self.assertTrue(any('SL_WRONG_DIRECTION' in i for i in result['issues']))


class MockClient:
    """Mock broker client for testing."""
    
    def __init__(self, trades=None, repair_success=True, close_success=True):
        self.trades = trades or []
        self.repair_success = repair_success
        self.close_success = close_success
        self.repairs_attempted = []
        self.closes_attempted = []
    
    def list_open_trades(self):
        return {'trades': self.trades}
    
    def create_stop_loss(self, trade_id, price):
        self.repairs_attempted.append({'trade_id': trade_id, 'sl': price})
        if not self.repair_success:
            raise Exception('Mock repair failed')
        return {'success': True}
    
    def create_take_profit(self, trade_id, price):
        self.repairs_attempted.append({'trade_id': trade_id, 'tp': price})
        if not self.repair_success:
            raise Exception('Mock repair failed')
        return {'success': True}
    
    def close_trade(self, trade_id):
        self.closes_attempted.append(trade_id)
        if not self.close_success:
            raise Exception('Mock close failed')
        return {'success': True}
    
    def close_position(self, instrument):
        self.closes_attempted.append(instrument)
        if not self.close_success:
            raise Exception('Mock close failed')
        return {'success': True}


class TestOCOReconcileIntegration(unittest.TestCase):
    """Integration tests for OCO reconcile with mock broker."""
    
    def test_reconcile_detects_missing_oco(self):
        """Test that reconcile detects and emits OCO_MISSING for unprotected trades."""
        from multi_broker_phoenix.risk.oco_reconcile import run_oco_reconcile_once
        
        # Trade without SL/TP
        trades = [{
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '1000',
            'price': '1.1000',
        }]
        
        client = MockClient(trades=trades, repair_success=False)
        config = {
            'enabled': True,
            'auto_repair': True,
            'auto_flatten': False,  # Disable flatten for this test
            'repair_attempts': 1,
            'repair_backoff_sec': 0.01,
        }
        
        result = run_oco_reconcile_once(client, config)
        
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['missing'], 1)
        self.assertEqual(result['ok'], 0)
        # Repair was attempted
        self.assertGreater(len(client.repairs_attempted), 0)
    
    def test_repair_fail_emergency_flatten(self):
        """Test that failed repair + high risk triggers emergency flatten."""
        from multi_broker_phoenix.risk.oco_reconcile import run_oco_reconcile_once
        
        # Large trade without protections
        trades = [{
            'tradeID': '12345',
            'instrument': 'EUR_USD',
            'currentUnits': '100000',  # Large position
            'price': '1.1000',
        }]
        
        client = MockClient(trades=trades, repair_success=False, close_success=True)
        config = {
            'enabled': True,
            'auto_repair': True,
            'auto_flatten': True,
            'emergency_flatten_usd': 50.0,  # Low threshold to trigger flatten
            'repair_attempts': 1,
            'repair_backoff_sec': 0.01,
        }
        
        result = run_oco_reconcile_once(client, config)
        
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['missing'], 1)
        # Should have attempted flatten
        self.assertEqual(result['flattened'], 1)
        self.assertIn('12345', client.closes_attempted)


class TestBrokerHealth(unittest.TestCase):
    """Test broker health monitoring."""
    
    def test_health_state_initial(self):
        """Test initial health state."""
        from multi_broker_phoenix.risk.broker_health import get_health_state
        
        state = get_health_state()
        
        # Should have expected keys
        self.assertIn('healthy', state)
        self.assertIn('trading_allowed', state)
        self.assertIn('consecutive_failures', state)
    
    def test_disable_trading(self):
        """Test manual trading disable."""
        from multi_broker_phoenix.risk.broker_health import (
            disable_trading, is_trading_allowed, enable_trading_after_reconcile,
            _health_state
        )
        
        # Start with healthy state
        _health_state['healthy'] = True
        _health_state['trading_allowed'] = True
        
        disable_trading('test')
        self.assertFalse(is_trading_allowed())
        
        # Re-enable
        enable_trading_after_reconcile()
        self.assertTrue(is_trading_allowed())


if __name__ == '__main__':
    unittest.main(verbosity=2)
